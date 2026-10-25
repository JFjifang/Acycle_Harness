#!/usr/bin/env python3
"""Verify installed release files and MCP stdio without running scientific work.

Run using the dedicated venv that contains the built wheel. Extract the built
npm tarball into a separate directory and pass its package directory. The
optional native-registry check uses an existing official Harness installation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--version', default='0.5.1')
    parser.add_argument('--plugin-root', required=True, help='Extracted package/ from the npm tarball')
    parser.add_argument('--runtime', help='Official Harness package installation for native-registry smoke')
    parser.add_argument('--output', default='validation/release-verification.json')
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root/output
    output.parent.mkdir(parents=True, exist_ok=True)
    plugin_root = Path(args.plugin_root).resolve()
    wheel = root/'dist'/f'acycle_deepseek-{args.version}-py3-none-any.whl'
    sdist = root/'dist'/f'acycle_deepseek-{args.version}.tar.gz'
    plugin_archive = root/'dist'/f'dsh-acycle-{args.version}.tgz'
    import acycle_deepseek
    installed = Path(acycle_deepseek.__file__).resolve().parent
    assert installed.is_relative_to(Path(sys.prefix).resolve()), 'Use an independently installed wheel, not a source/PYTHONPATH import'
    assert importlib.metadata.version('acycle-deepseek') == args.version
    wheel_files = []
    with zipfile.ZipFile(wheel) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            if not name.startswith('acycle_deepseek/') or name.endswith('/'):
                continue
            relative = Path(name).relative_to('acycle_deepseek')
            assert '..' not in relative.parts
            source = root/'matlab'/relative.relative_to('matlab') if relative.parts[0] == 'matlab' else root/'src'/name
            assert archive.read(name) == (installed/relative).read_bytes() == source.read_bytes(), name
            wheel_files.append(name)
    plugin_files = []
    with tarfile.open(plugin_archive) as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            assert member.isfile(), f'Unexpected npm member type: {member.name}'
            relative = Path(member.name).relative_to('package')
            assert '..' not in relative.parts
            data = archive.extractfile(member).read()
            assert data == (root/'plugin'/relative).read_bytes() == (plugin_root/relative).read_bytes(), str(relative)
            if relative.parts[0] == 'skills':
                assert data == (root/relative).read_bytes(), str(relative)
            plugin_files.append(str(relative))
    assert json.loads((plugin_root/'package.json').read_text())['version'] == args.version
    sdist_files = ['README.md', 'MANIFEST.in', 'scripts/ci_request.py']
    sdist_files.extend(str(path.relative_to(root)) for path in sorted((root/'tests/fixtures').glob('*')) if path.is_file())
    with tarfile.open(sdist) as archive:
        for relative in sdist_files:
            member = f'acycle_deepseek-{args.version}/{relative}'
            assert archive.extractfile(member).read() == (root/relative).read_bytes(), member

    requests = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
         'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                    'clientInfo': {'name': 'acycle-release-verifier', 'version': args.version}}},
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
        {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
         'params': {'name': 'acycle_capabilities', 'arguments': {}}},
    ]
    subprocess_env = {key: value for key, value in os.environ.items() if key != 'DEEPSEEK_API_KEY'}
    completed = subprocess.run([sys.executable, '-m', 'acycle_deepseek.mcp', '--workspace', str(root)],
        input='\n'.join(json.dumps(request) for request in requests)+'\n', text=True,
        capture_output=True, check=True, timeout=60, env=subprocess_env)
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    assert len(responses) == 3
    assert responses[0]['result']['serverInfo']['version'] == args.version
    names = [tool['name'] for tool in responses[1]['result']['tools']]
    assert len(names) == 12 and 'acycle_tune' in names and 'acycle_import_attachment' not in names
    capabilities = json.loads(responses[2]['result']['content'][0]['text'])
    assert capabilities['version'] == args.version and capabilities['python_numerical_fallback'] is False

    native = None
    if args.runtime:
        env = dict(subprocess_env, ACYCLE_PYTHON=sys.executable)
        checked = subprocess.run(['node', str(root/'scripts/installed_plugin_smoke.mjs'),
                                  str(Path(args.runtime).resolve()), str(root), str(plugin_root/'index.mjs')],
                                 env=env, capture_output=True, text=True, check=True, timeout=120)
        native = json.loads(checked.stdout)
        assert native['status'] == 'passed'
        assert len(native['registered_tools']) == 13 and len(native['registered_skills']) == 10
        (output.parent/'native-plugin-smoke.json').write_text(json.dumps(native, indent=2)+'\n')

    receipt = {
        'version': args.version, 'status': 'passed',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'python_executable': sys.executable, 'installed_python_root': str(installed),
        'installed_plugin_root': str(plugin_root),
        'wheel_sha256': digest(wheel), 'plugin_sha256': digest(plugin_archive), 'sdist_sha256': digest(sdist),
        'wheel_files_match_installed_and_source': wheel_files,
        'plugin_files_match_installed_and_source': plugin_files,
        'sdist_readme_manifest_and_fixture_files_match_source': sdist_files,
        'matlab_sources_installed': str(installed/'matlab'),
        'native_plugin_smoke': 'native-plugin-smoke.json' if native else None,
        'installed_mcp_stdio': {'initialize': 'passed', 'version': args.version,
            'listed_tools': len(names), 'tool_names': names, 'capabilities_call': 'passed',
            'scope': 'Installed wheel subprocess protocol; no local scientific MATLAB or full GUI session.'},
        'scope': 'Package/source/independent-install byte parity; actual MCP protocol and optional official Harness registry smoke. Scientific and live conversation evidence is separate.',
    }
    output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({'status': 'passed', 'wheel_files': len(wheel_files),
                      'plugin_files': len(plugin_files), 'mcp_tools': len(names),
                      'native_tools': len(native['registered_tools']) if native else None,
                      'receipt': str(output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
