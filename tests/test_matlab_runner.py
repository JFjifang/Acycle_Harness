"""Real process supervision tests; no MATLAB or scientific reference is mocked."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from acycle_deepseek.matlab_runner import run_matlab


def run(tmp_path, program, **budgets):
    marker = tmp_path / 'started.json'
    command = [sys.executable, '-u', '-c', program, str(marker)]
    return run_matlab(command, tmp_path, startup_marker=marker, **budgets)


def test_started_process_preserves_stdout_stderr(tmp_path):
    result = run(tmp_path, "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('{}');print('stdout');print('stderr',file=sys.stderr)")
    assert result.returncode == 0
    receipt = json.loads((tmp_path/'matlab-launch.json').read_text())
    assert receipt['startup_observed']
    assert receipt['attempts'] == 1 and not receipt['automatic_retry']
    log = (tmp_path/'matlab.log').read_text()
    assert 'stdout' in log and 'stderr' in log
    before = (tmp_path/'matlab-launch.json').read_bytes()
    with pytest.raises(RuntimeError, match='overwrite'):
        run(tmp_path, "print('should never execute')")
    assert (tmp_path/'matlab-launch.json').read_bytes() == before


@pytest.mark.parametrize('started,status', [(False,'startup_timeout'), (True,'execution_timeout')])
def test_stuck_process_is_stopped_and_failure_evidence_retained(tmp_path, started, status):
    program = "import time,pathlib,sys;print('startup diagnostic',flush=True);"
    if started:
        program += "pathlib.Path(sys.argv[1]).write_text('{}');"
    program += "time.sleep(60)"
    with pytest.raises(TimeoutError):
        run(tmp_path, program, startup_timeout=0.3, timeout=0.6)
    receipt = json.loads((tmp_path/'matlab-launch.json').read_text())
    assert receipt['status'] == status
    assert receipt['returncode'] is not None
    assert receipt['attempts'] == 1
    assert 'startup diagnostic' in (tmp_path/'matlab.log').read_text()


def test_process_crash_does_not_retry(tmp_path):
    result = run(tmp_path, "import sys;print('ServiceHost failure',file=sys.stderr);sys.exit(12)")
    assert result.returncode == 12
    receipt = json.loads((tmp_path/'matlab-launch.json').read_text())
    assert receipt['status'] == 'process_failed' and not receipt['startup_observed']
    assert receipt['attempts'] == 1


@pytest.mark.skipif(os.name == 'nt', reason='POSIX signal cancellation contract')
def test_parent_cancellation_stops_launched_group_and_saves_receipt(tmp_path):
    driver = tmp_path/'driver.py'
    driver.write_text("from pathlib import Path\nimport sys\nfrom acycle_deepseek.matlab_runner import run_matlab\np=Path(sys.argv[1]);run_matlab([sys.executable,'-u','-c','import time;print(123,flush=True);time.sleep(60)'],p,startup_marker=p/'started',startup_timeout=30)\n")
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    worker = subprocess.Popen([sys.executable, str(driver), str(tmp_path)], env=env)
    receipt_path=tmp_path/'matlab-launch.json'
    try:
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            if receipt_path.exists():
                try:
                    if json.loads(receipt_path.read_text()).get('pid'): break
                except ValueError: pass
            time.sleep(.02)
        worker.send_signal(signal.SIGTERM)
        worker.wait(timeout=10)
        receipt=json.loads(receipt_path.read_text())
        assert receipt['status']=='interrupted'
        assert receipt['returncode'] is not None
        with pytest.raises(ProcessLookupError): os.kill(receipt['pid'],0)
    finally:
        if worker.poll() is None: worker.kill();worker.wait()
