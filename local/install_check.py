#!/usr/bin/env python3
"""Check an installed release and optional native plugin without API or MATLAB calls."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid
import zipfile

VERSION = '0.4.0'
TOOLS = {'acycle_capabilities', 'acycle_inspect', 'acycle_analyze', 'acycle_swa',
         'acycle_coco', 'acycle_ecoco', 'acycle_rerun', 'acycle_sensitivity',
         'acycle_compare', 'acycle_get_run'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--bundle-root', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--runtime', help='Optional project-local official Harness npm installation')
    parser.add_argument('--output', help='New JSON receipt path; default is unique under workspace/local-validation')
    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    bundle = Path(args.bundle_root).expanduser().resolve()
    destination = Path(args.output).expanduser().resolve() if args.output else workspace/'local-validation'/(
        datetime.now(timezone.utc).strftime('install-%Y%m%dT%H%M%SZ-')+uuid.uuid4().hex[:8]+'.json')
    if destination.exists():
        parser.error(f'Refusing to overwrite receipt: {destination}')
    workspace.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    for name in ('PYTHONPATH', 'PYTHONHOME', 'DEEPSEEK_API_KEY'):
        environment.pop(name, None)
    environment['ACYCLE_PYTHON'] = sys.executable
    environment['ACYCLE_WORKSPACE'] = str(workspace)
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'expected_version': VERSION,
              'python_executable': sys.executable, 'workspace': str(workspace), 'bundle_root': str(bundle),
              'status': 'running', 'checks': {}, 'errors': [], 'api_called': False,
              'matlab_executed': False, 'host_configuration_modified': False,
              'scope': 'Installed-package, MCP and optional native-registry checks only. These do not establish real-model, scientific or GUI acceptance.'}

    def run(command, *, input_text=None):
        result = subprocess.run(command, cwd=workspace, env=environment, input=input_text,
                                capture_output=True, text=True, timeout=120, check=False)
        if result.returncode:
            raise RuntimeError(f'Check process exited {result.returncode}: {result.stderr[-3000:]}')
        return result.stdout

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    try:
        probe = '''import importlib.metadata,json
from pathlib import Path
import acycle_deepseek
from acycle_deepseek.tools import _matlab_dir,tool_schemas
print(json.dumps({'version':importlib.metadata.version('acycle-deepseek'),'package_root':str(Path(acycle_deepseek.__file__).parent),'matlab_root':str(_matlab_dir()),'tools':[item['function']['name'] for item in tool_schemas()]}))'''
        installed = json.loads(run([sys.executable, '-I', '-c', probe]))
        require(installed['version'] == VERSION, 'Install the matching 0.4.0 package in this Python environment')
        require(set(installed['tools']) == TOOLS, 'Installed shared tool set does not match this release')
        bridge = Path(installed['matlab_root'])
        for name in ('acycle_batch.m', 'acycle_swa.m', 'acycle_coco.m',
                     'source_registry.json', 'swa_sources.json', 'coco_sources.json'):
            require((bridge/name).is_file(), f'MATLAB bridge missing: {name}')
        report['checks']['python_package'] = {'status': 'passed', **installed}

        wheel = bundle/'dist'/f'acycle_deepseek-{VERSION}-py3-none-any.whl'
        npm = bundle/'dist'/f'dsh-acycle-{VERSION}.tgz'
        packages = {'status': 'not_run', 'reason': 'Release archives absent; source installation may still be valid.'}
        if wheel.is_file() and npm.is_file():
            hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (wheel, npm)}
            manifest = bundle/'dist/SHA256SUMS.json'
            if manifest.is_file():
                expected = json.loads(manifest.read_text(encoding='utf-8'))
                require(all(expected.get(name) == value for name, value in hashes.items()), 'Release archive checksum mismatch')
            with zipfile.ZipFile(wheel) as archive:
                require(archive.testzip() is None, 'Wheel CRC check failed')
                members = [name for name in archive.namelist() if name.startswith('acycle_deepseek/')
                           and name.endswith(('.py', '.m', '.json', '.md'))]
                for name in members:
                    path = Path(installed['package_root'])/name.removeprefix('acycle_deepseek/')
                    # An editable source install keeps MATLAB beside src/ instead of inside the package.
                    if name.startswith('acycle_deepseek/matlab/'):
                        path = bridge/name.removeprefix('acycle_deepseek/matlab/')
                    require(path.is_file() and path.read_bytes() == archive.read(name), f'Installed file differs from wheel: {name}')
            with tarfile.open(npm) as archive:
                metadata = json.load(archive.extractfile('package/package.json'))
                require(metadata['version'] == VERSION, 'Native archive version mismatch')
                skills = [name for name in archive.getnames() if name.endswith('/SKILL.md')]
                require(len(skills) == 8, 'Native archive must contain eight skills')
                for name in ('package/index.mjs', 'package/attachments.mjs', 'package/cordis.patch.yml'):
                    require(name in archive.getnames(), f'Native archive missing {name}')
            packages = {'status': 'passed', 'sha256': hashes, 'installed_files_match_wheel': True,
                        'native_archive_skills': len(skills)}
        report['checks']['release_archives'] = packages

        requests = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'local-install-check', 'version': VERSION}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'acycle_capabilities', 'arguments': {}}},
        ]
        responses = {message['id']: message for message in map(json.loads, run(
            [sys.executable, '-I', '-m', 'acycle_deepseek.mcp', '--workspace', str(workspace)],
            input_text=''.join(json.dumps(item)+'\n' for item in requests)).splitlines())}
        require(responses[1]['result']['serverInfo']['version'] == VERSION, 'MCP version mismatch')
        require({tool['name'] for tool in responses[2]['result']['tools']} == TOOLS, 'MCP tool set mismatch')
        require(not responses[3]['result'].get('isError'), 'MCP capabilities call failed')
        capability = json.loads(responses[3]['result']['content'][0]['text'])
        require(capability['version'] == VERSION and capability['python_numerical_fallback'] is False, 'MCP capabilities mismatch')
        report['checks']['mcp'] = {'status': 'passed', 'version': VERSION, 'tools': sorted(TOOLS),
                                   'capabilities_called': True, 'scientific_tool_called': False}

        report['checks']['native_plugin'] = {'status': 'not_run', 'reason': 'Pass --runtime for the installed official Harness registry check.'}
        if args.runtime:
            runtime = Path(args.runtime).expanduser().resolve()
            plugin = runtime/'node_modules/dsh-acycle/index.mjs'
            node = shutil.which('node')
            require(node is not None, 'Install compatible Node.js to check the native plugin')
            require(plugin.is_file(), 'Install the release npm tarball into the specified runtime first')
            installed_plugin_matches_archive = None
            if npm.is_file():
                with tarfile.open(npm) as archive:
                    for member in archive.getmembers():
                        if not member.isfile():
                            continue
                        relative = Path(member.name.removeprefix('package/'))
                        require(not relative.is_absolute() and '..' not in relative.parts, 'Unexpected native archive path')
                        installed_file = plugin.parent/relative
                        require(installed_file.is_file() and installed_file.read_bytes() == archive.extractfile(member).read(),
                                f'Installed native file differs from release archive: {relative}')
                installed_plugin_matches_archive = True
            outcome = json.loads(run([node, str(bundle/'scripts/installed_plugin_smoke.mjs'),
                                      str(runtime), str(workspace), str(plugin)]))
            require(outcome.get('status') == 'passed', 'Native registry check failed')
            require(set(outcome['registered_tools']) == TOOLS | {'acycle_import_attachment'}, 'Native tool set mismatch')
            require(len(outcome['registered_skills']) == 8, 'Native skill count mismatch')
            require(outcome['capabilities']['version'] == VERSION, 'Native bridge version mismatch')
            outcome['installed_files_match_archive'] = installed_plugin_matches_archive
            report['checks']['native_plugin'] = outcome
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['errors'].append(f'{type(error).__name__}: {error}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'receipt': str(destination), 'checks': {
        name: value['status'] for name, value in report['checks'].items()}, 'errors': report['errors']}, ensure_ascii=False))
    return 1 if report['status'] == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
