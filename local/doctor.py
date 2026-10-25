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
import uuid

REFERENCE = 'dcba4279168745b563e0535b954297023dd62fc7'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--run-matlab', action='store_true', help='Actually start MATLAB and check runtime functions/toolboxes')
    parser.add_argument('--startup-timeout', type=float, default=180)
    parser.add_argument('--matlab-timeout', type=float, default=300)
    parser.add_argument('--harness-deployment', help='Generated private Web deployment.json to inspect')
    parser.add_argument('--check-harness', action='store_true', help='Boot a separate private Web composition and inspect actual agent/model/skills without an API call')
    parser.add_argument('--output', help='Optional JSON receipt; default prints only')
    args = parser.parse_args()
    if args.startup_timeout <= 0 or args.matlab_timeout <= 0:
        parser.error('Timeouts must be positive')
    if args.check_harness and not args.harness_deployment:
        parser.error('--check-harness requires --harness-deployment')
    if args.output and Path(args.output).expanduser().exists():
        parser.error('Choose a new --output path; previous diagnostic receipts are preserved')
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
        if report['package_version'] != '0.5.0' or len(report['registered_tools']) != 12:
            report['errors'].append('This handoff requires matching acycle-deepseek 0.5.0 with 12 shared tools')
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
        scratch = workspace/'.acycle'/'diagnostics'
        scratch.mkdir(parents=True, exist_ok=True)
        if not scratch.resolve().is_relative_to(workspace):
            raise ValueError('MATLAB diagnostics must remain inside the workspace')
        folder = scratch/(datetime.now(timezone.utc).strftime('doctor-%Y%m%dT%H%M%SZ-')+uuid.uuid4().hex[:8])
        folder.mkdir()
        report['matlab_diagnostics_directory'] = str(folder)
        report['automatic_matlab_retry'] = False
        try:
            from acycle_deepseek.matlab_runner import run_matlab
            response = folder/'probe.json'
            marker = folder/'matlab-started.json'
            q = lambda value: "'"+str(value).replace("'", "''")+"'"
            expression = ';'.join([
                f"fid=fopen({q(marker)},'w');fprintf(fid,'%s','{{\"started\":true}}');fclose(fid)",
                "r=struct('release',version('-release'),'version',version,'toolboxes',ver)",
                "names={'pmtm','chi2inv','smooth','hilbert'}",
                "r.required_functions=cellfun(@which,names,'UniformOutput',false)",
                f"fid=fopen({q(response)},'w')",
                "fprintf(fid,'%s',jsonencode(r));fclose(fid)",
                "assert(all(~cellfun(@isempty,r.required_functions)),'Required MATLAB toolbox function missing')",
            ])+';'
            completed = run_matlab([executable, '-batch', expression], folder, startup_marker=marker,
                                   startup_timeout=args.startup_timeout, timeout=args.matlab_timeout)
            report['matlab_exit_code'] = completed.returncode
            if response.is_file():
                report['matlab_runtime'] = json.loads(response.read_text(encoding='utf-8'))
            report['matlab_runtime_checked'] = completed.returncode == 0 and marker.is_file() and response.is_file()
            if not report['matlab_runtime_checked']:
                report['errors'].append(f'MATLAB startup/toolbox probe failed. Inspect retained evidence in {folder}; no automatic retry was made.')
        except (ImportError, OSError, RuntimeError, TimeoutError, ValueError) as error:
            report['errors'].append(f'MATLAB probe: {type(error).__name__}: {error}. Evidence directory: {folder}; no automatic retry was made.')
        report['matlab_log'] = str(folder/'matlab.log')
        report['matlab_launch_receipt'] = str(folder/'matlab-launch.json')
    elif not args.run_matlab:
        report['warnings'].append('Executable detection does not establish license/toolbox readiness; rerun with --run-matlab')
    if args.harness_deployment:
        deployment_path = Path(args.harness_deployment).expanduser().resolve()
        try:
            deployment = json.loads(deployment_path.read_text(encoding='utf-8'))
            runtime = Path(deployment['runtime'])
            installed = json.loads((runtime/'node_modules/@deepseek-ai/dsh/package.json').read_text())
            report['harness'] = {'deployment': str(deployment_path), 'version': installed['version'],
                'expected_version': deployment['harness_version'], 'profile': deployment['profile'],
                'preset': deployment['preset'], 'provider': deployment['provider'], 'model': deployment['model'],
                'actual_agent_checked': False, 'legacy_desktop_modified': False}
            if installed['version'] != '0.2.1-rc.3':
                report['errors'].append('Supported native Web runtime is pinned to 0.2.1-rc.3; keep the legacy Desktop separate')
            if args.check_harness:
                target = workspace/'local-validation'/('agent-composition-'+uuid.uuid4().hex[:12]+'.json')
                completed = subprocess.run([sys.executable, str(Path(__file__).with_name('check_harness.py')),
                    '--deployment', str(deployment_path), '--output', str(target)], capture_output=True, text=True, check=False)
                report['harness']['composition_receipt'] = str(target)
                if target.is_file():
                    result = json.loads(target.read_text())
                    report['harness']['actual_agent_checked'] = result.get('status') == 'passed'
                    report['harness']['resolved_model'] = result.get('model')
                    report['harness']['scoped_skills'] = result.get('skills', [])
                    report['harness']['persona_present'] = result.get('persona_present', False)
                    report['harness']['skills_in_model_messages'] = result.get('skills_in_model_messages', False)
                if completed.returncode or not report['harness']['actual_agent_checked']:
                    report['errors'].append(f'Actual Harness agent composition check failed; inspect {target}')
            else:
                report['warnings'].append('Harness version/config detection does not establish actual agent composition; add --check-harness')
        except (KeyError, OSError, ValueError) as error:
            report['errors'].append(f'Harness deployment inspection: {type(error).__name__}: {error}')
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
