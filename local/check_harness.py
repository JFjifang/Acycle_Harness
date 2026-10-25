#!/usr/bin/env python3
"""Boot the generated Web composition in a temporary private home and inspect a real agent."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--deployment', default='local/generated/harness-web/deployment.json')
parser.add_argument('--output', required=True, help='New JSON receipt; also writes its assembled prompt evidence')
args = parser.parse_args()
deployment = json.loads(Path(args.deployment).expanduser().read_text(encoding='utf-8'))
output = Path(args.output).expanduser().resolve()
if output.exists():
    parser.error(f'Refusing to overwrite {output}')
output.parent.mkdir(parents=True, exist_ok=True)
bundle = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='acycle-agent-check-', dir=output.parent) as folder:
    temporary = Path(folder)
    private_home = temporary/'home'
    shutil.copytree(Path(deployment['dsh_home'])/'profiles/web', private_home/'profiles/web')
    overlay = temporary/'probe.patch.yml'
    overlay.write_text(json.dumps([{'insert': [{'id': 'acycle-composition-probe',
        'name': (bundle/'local/harness_probe.mjs').as_uri(), 'config': {
            'runtime': deployment['runtime'], 'preset': deployment['preset'],
            'workspace': deployment['workspace'], 'output': str(output),
            'expectedVersion': deployment.get('acycle_version', '0.5.0'),
            'expectedNativeTools': deployment.get('expected_native_tools', 13),
            'expectedSkills': deployment.get('expected_skills', 10),
            'expectedTotalSkills': deployment.get('expected_total_skills', 10),
            'demoSkill': deployment.get('newark_demo', {}).get('skill_name')}}]}], indent=2)+'\n')
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    environment = {**os.environ, **deployment['environment'], 'DSH_HOME': str(private_home)}
    environment.pop('DEEPSEEK_API_KEY', None)
    command = [deployment['node'], deployment['cli'], '--profile', 'web', '--patch', str(overlay),
               '--host', '127.0.0.1', '--port', str(port), '--no-open']
    with (temporary/'startup.log').open('w') as log:
        process = subprocess.Popen(command, cwd=deployment['workspace'], env=environment,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name != 'nt')
        try:
            deadline = time.monotonic()+120
            while time.monotonic() < deadline and not output.is_file() and process.poll() is None:
                time.sleep(.2)
            if not output.is_file():
                # Do not copy Web bearer URLs or inherited environment into the receipt.
                lines = (temporary/'startup.log').read_text(errors='replace').splitlines()
                safe = [line for line in lines if 'http://' not in line and 'https://' not in line]
                output.write_text(json.dumps({'status': 'failed', 'actual_agent_created': False,
                    'model_api_called': False, 'matlab_executed': False,
                    'error': 'No agent-composition receipt before exit/timeout', 'startup_diagnostic': safe[-30:]}, indent=2)+'\n')
        finally:
            if process.poll() is None:
                if os.name == 'nt':
                    process.terminate()
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    if os.name == 'nt':
                        process.kill()
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
report = json.loads(output.read_text())
print(json.dumps({'status': report['status'], 'receipt': str(output), 'actual_agent_created': report.get('actual_agent_created'),
                  'preset': report.get('selected_preset'), 'skills': len(report.get('skills', [])),
                  'total_scoped_skills': len(report.get('all_scoped_skills', [])),
                  'model_api_called': False, 'matlab_executed': False}))
raise SystemExit(0 if report['status'] == 'passed' else 1)
