#!/usr/bin/env python3
"""Launch the generated private Web deployment with its MATLAB environment."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--deployment', default='local/generated/harness-web/deployment.json')
parser.add_argument('--dump-config', action='store_true')
parser.add_argument('--patch', action='append', default=[], help='Explicit extra test overlay; does not edit the profile')
args = parser.parse_args()
deployment = json.loads(Path(args.deployment).expanduser().read_text(encoding='utf-8'))
environment = {**os.environ, **deployment['environment']}
command = [deployment['node'], deployment['cli'], '--profile', deployment['profile']]
for patch in args.patch:
    command.extend(['--patch', str(Path(patch).expanduser().resolve())])
command.extend(['--dump-config'] if args.dump_config else ['--host', '127.0.0.1', '--port', str(deployment['port']), '--no-open'])
raise SystemExit(subprocess.call(command, cwd=deployment['workspace'], env=environment))
