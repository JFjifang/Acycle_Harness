#!/usr/bin/env python3
"""Inspect local deployment; optional real MATLAB startup does no science."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REFERENCE = 'dcba4279168745b563e0535b954297023dd62fc7'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--run-matlab', action='store_true', help='Actually start MATLAB and check runtime functions/toolboxes')
    parser.add_argument('--output', help='Optional JSON receipt; default prints only')
    args = parser.parse_args()
    root_text = os.environ.get('ACYCLE_ROOT')
    root = Path(root_text).expanduser().resolve() if root_text else None
    workspace = Path(args.workspace).expanduser().resolve()
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version.split()[0],
              'python_executable': sys.executable, 'workspace': str(workspace),
              'backend': os.environ.get('ACYCLE_BACKEND', 'local'), 'reference_commit': REFERENCE,
              'acycle_root': str(root) if root else None, 'errors': [], 'warnings': []}
    try:
        from acycle_deepseek.tools import _matlab_dir, tool_schemas
        report['package_version'] = importlib.metadata.version('acycle-deepseek')
        report['registered_tools'] = [tool['function']['name'] for tool in tool_schemas()]
        bridge = _matlab_dir()
        report['matlab_bridge'] = str(bridge)
    except (ImportError, RuntimeError, importlib.metadata.PackageNotFoundError) as error:
        report['errors'].append(f'Python package unavailable: {error}')
        bridge = None
    command = os.environ.get('MATLAB_EXECUTABLE', 'matlab')
    executable = shutil.which(command)
    report['matlab_executable'] = executable
    if report['backend'] != 'local':
        report['errors'].append('This handoff checks local execution; set ACYCLE_BACKEND=local')
    if executable is None:
        report['errors'].append('MATLAB executable not found; set MATLAB_EXECUTABLE to its executable path')
    if root is None or not (root/'code'/'seriesanalysis').is_dir():
        report['errors'].append('ACYCLE_ROOT must point to the Acycle checkout, not its code/ subdirectory')
    elif bridge:
        command_result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=False) if shutil.which('git') else None
        report['installed_commit'] = command_result.stdout.strip() if command_result and command_result.returncode == 0 else 'unknown'
        if report['installed_commit'] != REFERENCE:
            report['warnings'].append('Checkout revision differs from the validated pin or has no Git metadata; inspect source hashes')
        checks = []
        for registry in sorted([bridge/'source_registry.json', *bridge.glob('*_sources.json')]):
            if not registry.is_file():
                continue
            content = json.loads(registry.read_text(encoding='utf-8'))
            for source in content.get('files', []):
                relative = source.get('relative_path')
                if not relative:
                    continue
                path = root/relative
                actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
                checks.append({'relative_path': relative, 'sha256': actual, 'matches_reference': actual == source.get('sha256')})
        report['source_files'] = checks
        if not checks or not all(check['matches_reference'] for check in checks):
            report['warnings'].append('One or more original source hashes are missing or changed; do not claim validated compatibility')
    report['matlab_runtime_checked'] = False
    if args.run_matlab and not report['errors']:
        workspace.mkdir(parents=True, exist_ok=True)
        scratch = workspace/'.acycle'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='doctor-', dir=scratch) as folder:
            response = Path(folder)/'probe.json'
            q = lambda value: "'"+str(value).replace("'", "''")+"'"
            expression = ';'.join([
                "r=struct('release',version('-release'),'version',version,'toolboxes',ver)",
                "names={'pmtm','chi2inv','smooth','hilbert'}",
                "r.required_functions=cellfun(@which,names,'UniformOutput',false)",
                f"fid=fopen({q(response)},'w')",
                "fprintf(fid,'%s',jsonencode(r));fclose(fid)",
                "assert(all(~cellfun(@isempty,r.required_functions)),'Required MATLAB toolbox function missing')",
            ])+';'
            try:
                completed = subprocess.run([executable, '-batch', expression], capture_output=True, text=True,
                                           timeout=300, check=False)
                report['matlab_exit_code'] = completed.returncode
                if response.is_file():
                    report['matlab_runtime'] = json.loads(response.read_text(encoding='utf-8'))
                report['matlab_runtime_checked'] = completed.returncode == 0
                if completed.returncode:
                    report['errors'].append('MATLAB failed to start/check toolboxes. Run matlab -batch "ver" in the same terminal to inspect licensing and dependencies')
            except subprocess.TimeoutExpired:
                report['errors'].append('MATLAB startup check exceeded 300 seconds; inspect local licensing/startup before analysis')
    elif not args.run_matlab:
        report['warnings'].append('Executable detection does not establish license/toolbox readiness; rerun with --run-matlab')
    report['status'] = 'failed' if report['errors'] else ('runtime_ready' if report['matlab_runtime_checked'] else 'configuration_detected')
    rendered = json.dumps(report, ensure_ascii=False, indent=2)+'\n'
    if args.output:
        path = Path(args.output).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
