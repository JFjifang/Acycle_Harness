#!/usr/bin/env python3
"""Generate project-local integration snippets; never edit host configuration."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
from deploy_harness import HARNESS_VERSION, build_agent_preset


def write_new(path: Path, text: str, force: bool) -> None:
    if path.exists() and path.read_text(encoding='utf-8') != text and not force:
        raise FileExistsError(f'Refusing to replace {path}; inspect it or use --force')
    path.write_text(text, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--acycle-root', required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--matlab', default=os.environ.get('MATLAB_EXECUTABLE') or shutil.which('matlab') or 'matlab')
    parser.add_argument('--output-dir', default='local/generated')
    parser.add_argument('--force', action='store_true', help='Replace generated snippets only')
    parser.add_argument('--newark-demo', action='store_true', help='Include the public Newark demonstration skill in the Desktop preset')
    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    root = Path(args.acycle_root).expanduser().resolve()
    candidate = shutil.which(os.path.expanduser(args.python))
    if candidate is None:
        parser.error('--python must name an existing executable or a command on PATH')
    # Resolving this symlink would bypass a virtualenv and lose its installed package.
    executable = Path(os.path.abspath(candidate))
    matlab = args.matlab
    if '/' in matlab or '\\' in matlab:
        matlab = os.path.abspath(os.path.expanduser(matlab))
    env = {'ACYCLE_BACKEND': 'local', 'ACYCLE_ROOT': str(root),
           'MATLAB_EXECUTABLE': matlab, 'ACYCLE_MATLAB_TIMEOUT': '3600',
           'ACYCLE_MATLAB_STARTUP_TIMEOUT': '180',
           'ACYCLE_PYTHON': str(executable), 'ACYCLE_WORKSPACE': str(workspace)}
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    toml = '\n'.join([
        '# Review and merge this section; do not replace an existing configuration file.',
        '[mcp_servers.acycle]', f'command = {quote(str(executable))}',
        'args = '+quote(['-m', 'acycle_deepseek.mcp', '--workspace', str(workspace)]),
        'startup_timeout_sec = 30', 'tool_timeout_sec = 3600',
        '', '[mcp_servers.acycle.env]',
        *[f'{key} = {quote(value)}' for key, value in env.items()], '',
    ])
    shell = '# Source this file from the terminal that launches Harness. No API key is stored here.\n'
    shell += ''.join(f'export {key}={shlex.quote(value)}\n' for key, value in env.items())
    powershell = '# Dot-source this file in the PowerShell session that launches Harness.\n'
    powershell += ''.join("$env:"+key+" = '"+value.replace("'", "''")+"'\n" for key, value in env.items())
    directory = Path(args.output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    preset, demo = build_agent_preset(bundle=Path(__file__).resolve().parents[1],
        python=str(executable), workspace=workspace, acycle=root, matlab=matlab,
        plugin_name='dsh-acycle', newark_demo=args.newark_demo)
    desktop_patch = [{'id': 'preset-acycle', 'config': preset}]
    desktop_manifest = {'harness_version': HARNESS_VERSION, 'preset': 'acycle',
        'package': 'dsh-acycle', 'install_via': 'Desktop plugin manager or Desktop-bundled dsh',
        'patch_file': str(directory/'desktop.preset.patch.yml'), 'newark_demo': demo,
        'host_configuration_modified': False, 'credentials_stored': False}
    outputs = {'codex-mcp.toml': toml, 'runtime.env.sh': shell, 'runtime.env.ps1': powershell,
        'desktop.preset.patch.yml': json.dumps(desktop_patch, ensure_ascii=False, indent=2)+'\n',
        'desktop-preset.json': json.dumps(desktop_manifest, ensure_ascii=False, indent=2)+'\n'}
    # Check all paths before writing any so a conflict cannot leave mixed snippets.
    for name, content in outputs.items():
        destination = directory/name
        if destination.exists() and destination.read_text(encoding='utf-8') != content and not args.force:
            raise FileExistsError(f'Refusing to replace {destination}; inspect it or use --force')
    for name, content in outputs.items():
        write_new(directory/name, content, args.force)
    print(json.dumps({'status': 'generated', 'files': [str(directory/name) for name in outputs],
                      'host_configuration_modified': False, 'api_key_written': False}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
