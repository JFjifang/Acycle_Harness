"""Bound one local MATLAB process group; keep every launch log and receipt.

This module supervises execution only. It does not calculate scientific data,
retry MATLAB, alter licensing, or kill unrelated/shared MATLAB services.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import time
import threading


def _stop(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


def run_matlab(command, output, *, startup_marker, startup_timeout=180, timeout=1800):
    """Launch once, distinguish startup timeout from computation timeout.

    The caller puts the marker-writing expression first in MATLAB -batch. A
    process merely being alive never counts as successful MATLAB startup.
    """
    if startup_timeout <= 0 or timeout <= 0:
        raise ValueError('MATLAB startup and execution timeouts must be positive')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / 'matlab.log'
    lifecycle = output / 'matlab-launch.json'
    if lifecycle.exists() or log_path.exists() or Path(startup_marker).exists():
        raise RuntimeError('Refusing to overwrite existing MATLAB launch evidence')
    receipt = {'attempts': 1, 'automatic_retry': False, 'status': 'launching',
               'stdout_stderr_log': str(log_path), 'startup_marker': str(startup_marker),
               'startup_timeout_seconds': startup_timeout, 'execution_timeout_seconds': timeout,
               'launched_process_group_only': True, 'command': command}

    def save():
        lifecycle.write_text(json.dumps(receipt, indent=2) + '\n')

    started = time.monotonic()
    process = None
    previous_term = None
    if threading.current_thread() is threading.main_thread():
        previous_term = signal.getsignal(signal.SIGTERM)
        def terminated(signum, _frame):
            raise SystemExit(128 + signum)
        signal.signal(signal.SIGTERM, terminated)
    save()
    try:
        with log_path.open('x', encoding='utf-8') as log:
            kwargs = {'start_new_session': True} if os.name != 'nt' else {
                'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, shell=False, **kwargs)
            receipt.update(pid=process.pid, status='starting')
            save()
            startup_seen = False
            while process.poll() is None:
                elapsed = time.monotonic() - started
                if not startup_seen and Path(startup_marker).is_file():
                    startup_seen = True
                    receipt.update(status='running', startup_seconds=elapsed)
                    save()
                if not startup_seen and elapsed >= startup_timeout:
                    receipt['status'] = 'startup_timeout'
                    raise TimeoutError(f'MATLAB did not reach its batch entry within {startup_timeout}s; retained {log_path}')
                if elapsed >= timeout:
                    receipt['status'] = 'execution_timeout'
                    raise TimeoutError(f'MATLAB exceeded the execution budget of {timeout}s; retained {log_path}')
                time.sleep(min(0.1, startup_timeout / 10, timeout / 10))
            receipt.update(returncode=process.returncode,
                           startup_observed=Path(startup_marker).is_file(),
                           status='exited' if process.returncode == 0 else 'process_failed')
            return subprocess.CompletedProcess(command, process.returncode)
    except BaseException as error:
        if receipt['status'] not in {'startup_timeout', 'execution_timeout'}:
            receipt['status'] = 'interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'launch_failed'
        receipt['error'] = f'{type(error).__name__}: {error}'
        if process is not None:
            _stop(process)
            receipt['returncode'] = process.returncode
        raise
    finally:
        if previous_term is not None:
            signal.signal(signal.SIGTERM, previous_term)
        receipt['elapsed_seconds'] = time.monotonic() - started
        save()
