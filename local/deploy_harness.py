#!/usr/bin/env python3
"""Create a project-local Web/native deployment of the current supported Harness release."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HARNESS_VERSION = '0.2.1-rc.3'
PERSONA = '''You are the Acycle MATLAB research assistant. This is the Acycle research deployment.
Use the installed Acycle skills and native acycle_* tools for scientific work. Scientific QA, statistics, interpolation, tuning, spectral calculations and plots must run through MATLAB. Python may transport files or inspect their structure; it is not a replacement numerical backend. Preserve original inputs, completed baselines and failed-run evidence. Change a completed analysis with acycle_rerun, retaining its operation and undeclared settings. After a MATLAB startup failure stop and report the saved diagnostic; do not retry through sandbox shell or delete logs.
Check units, age/target assumptions and a justified search range before rate or chronology analysis; ask concise questions when these facts are missing. Do not infer hidden geological identity from filenames or spectra.
Deliver the key MATLAB figures in the final answer using the verified display_markdown returned by tools, with run IDs and original downloadable files. Automatic offloaded previews do not establish model visual inspection. If the selected model supports image input, use read_image to inspect existing PNGs when useful, and report a failed or unavailable visual check honestly. Model image transport, user-visible main Chat rendering and numerical validation are separate claims. Do not invent artifact URLs, scientific findings or unsupported capabilities.'''


def build_agent_preset(*, bundle: Path, python: str, workspace: Path, acycle: Path,
                       matlab: str, plugin_name: str, newark_demo: bool = False):
    """The same current native agent composition is used by Web and Desktop."""
    demo = {'enabled': newark_demo}
    persona = PERSONA
    if newark_demo:
        demo_root = bundle/'demo/newark-0.5.1'
        provider = bundle/'scripts/harness_conversation_support.mjs'
        skill = demo_root/'skills/newark-relative-time-demo/SKILL.md'
        sources = [demo_root/'manifest.json', demo_root/'SOURCES.md', demo_root/'literature_sources.json', skill, provider]
        if any(not path.is_file() for path in sources):
            raise ValueError('The complete public Newark demo and its skill provider must be included in this handoff')
        demo.update(skill_name='newark-relative-time-demo', autonomy_class='preset-assisted',
                    sources=[{'relative_path': str(path.relative_to(bundle)),
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in sources])
        persona += f'\nThis deployment explicitly includes the public Newark demonstration. When the user selects that demonstration, load the newark-relative-time-demo skill and read its public manifest at {demo_root / "manifest.json"} and sources at {demo_root / "SOURCES.md"}. Do not apply its priors to other data.'
    agent_plugins = [
        {'id': 'acycle-persona', 'name': '@deepseek-ai/dsh-persona', 'config': {'prefix': persona}},
        {'id': 'acycle-native', 'name': plugin_name, 'config': {'python': python, 'workspace': str(workspace),
            'acycleRoot': str(acycle), 'matlabExecutable': matlab, 'backend': 'local'}},
        {'id': 'acycle-skill-reader', 'name': '@deepseek-ai/dsh-tool-skill'},
        {'id': 'acycle-file-reader', 'name': '@deepseek-ai/dsh-tool-fs', 'config': {'read': True, 'readImage': True, 'write': False, 'edit': False}},
        {'id': 'acycle-present', 'name': '@deepseek-ai/dsh-tool-present'},
        {'id': 'acycle-ask-user', 'name': '@deepseek-ai/dsh-tool-ask-user'},
    ]
    if newark_demo:
        agent_plugins.append({'id': 'acycle-newark-public-demo', 'name': provider.as_uri(),
                              'config': {'skillPath': str(skill)}})
    return {'id': 'acycle', 'name': 'Acycle MATLAB',
            'description': 'MATLAB research with Acycle skills and original figures',
            'order': 0, 'plugins': agent_plugins}, demo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--acycle-root', required=True)
    parser.add_argument('--directory', default='local/generated/harness-web')
    parser.add_argument('--runtime', help='Existing pinned runtime; default is directory/runtime')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--matlab', default=os.environ.get('MATLAB_EXECUTABLE', 'matlab'))
    parser.add_argument('--plugin', help='Explicit native index.mjs for development; default is installed dsh-acycle')
    parser.add_argument('--package', help='Native tgz for --install; default is dist/dsh-acycle-0.5.1.tgz')
    parser.add_argument('--install', action='store_true', help='Install pinned npm runtime and local native package into the deployment only')
    parser.add_argument('--newark-demo', action='store_true', help='Explicitly mount the public Newark demonstration skill in the actual agent preset')
    parser.add_argument('--port', type=int, default=3080)
    parser.add_argument('--force', action='store_true', help='Replace this generated deployment configuration')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    workspace = Path(args.workspace).expanduser().resolve()
    directory = Path(args.directory).expanduser().resolve()
    runtime = Path(args.runtime).expanduser().resolve() if args.runtime else directory/'runtime'
    acycle = Path(args.acycle_root).expanduser().resolve()
    python = shutil.which(os.path.expanduser(args.python))
    if python is None:
        parser.error('--python must name an installed executable')
    python = os.path.abspath(python)  # Preserve the virtualenv symlink.
    node = shutil.which('node')
    if node is None:
        parser.error('Node.js >=24.9 is required')
    version = subprocess.check_output([node, '--version'], text=True).strip()
    numbers = tuple(int(part) for part in version.lstrip('v').split('.')[:2])
    if numbers < (24, 9):
        parser.error(f'Node.js >=24.9 is required; found {version}')
    bundle = Path(__file__).resolve().parents[1]
    if args.install:
        npm = shutil.which('npm')
        if npm is None:
            parser.error('npm is required for --install')
        archive = Path(args.package).expanduser().resolve() if args.package else bundle/'dist/dsh-acycle-0.5.1.tgz'
        if not archive.is_file():
            parser.error(f'Native release package missing: {archive}')
        runtime.mkdir(parents=True, exist_ok=True)
        subprocess.run([npm, 'install', '--prefix', str(runtime), '--cache', str(directory/'npm-cache'),
                        '--save-exact', f'@deepseek-ai/dsh@{HARNESS_VERSION}',
                        f'@deepseek-ai/dsh-web-frontend@{HARNESS_VERSION}',
                        f'@deepseek-ai/dsh-sdk-client@{HARNESS_VERSION}', str(archive)], check=True)
    for name in ('dsh', 'dsh-web-frontend', 'dsh-sdk-client'):
        package = runtime/f'node_modules/@deepseek-ai/{name}/package.json'
        if not package.is_file() or json.loads(package.read_text())['version'] != HARNESS_VERSION:
            parser.error(f'Install @deepseek-ai/{name}@{HARNESS_VERSION}, or use --install')
    frontend = runtime/'node_modules/@deepseek-ai/dsh-web-frontend/dist/index.html'
    if not frontend.is_file():
        parser.error('The official dsh-web-frontend dist/index.html is missing; a registry-only runtime cannot serve Web')
    plugin = Path(args.plugin).expanduser().resolve() if args.plugin else runtime/'node_modules/dsh-acycle/index.mjs'
    if not plugin.is_file():
        parser.error(f'Native plugin missing: {plugin}')
    matlab = os.path.expanduser(args.matlab)
    if '/' in matlab or '\\' in matlab:
        matlab = os.path.abspath(matlab)
    home = directory/'home'
    profile = home/'profiles/web'
    try:
        preset, demo = build_agent_preset(bundle=bundle, python=python, workspace=workspace,
            acycle=acycle, matlab=matlab, plugin_name=plugin.as_uri(), newark_demo=args.newark_demo)
    except ValueError as error:
        parser.error(str(error))
    patch = [
        {'id': 'agent-preset-registry', 'config': {'default': 'acycle'}},
        {'id': 'agent-default-model', 'config': {'provider': 'deepseek-official', 'model': 'deepseek-flash'}},
        {'id': 'llm-deepseek', 'config': {'apiKeyEnv': 'DEEPSEEK_API_KEY', 'models': [
            {'id': 'deepseek-flash', 'name': 'DeepSeek Flash', 'inputModalities': ['text', 'image'], 'systemPromptUpdate': 'in-history'}]}},
        {'insert': [{'id': 'preset-acycle', 'name': '@deepseek-ai/dsh-agent-preset', 'config': preset}]},
    ]
    deployment = {'schema_version': 1, 'acycle_version': '0.5.1', 'expected_native_tools': 13,
                  'expected_skills': 10, 'harness_version': HARNESS_VERSION, 'profile': 'web', 'preset': 'acycle',
                  'expected_total_skills': 11 if args.newark_demo else 10, 'newark_demo': demo,
                  'workspace': str(workspace), 'directory': str(directory), 'runtime': str(runtime),
                  'dsh_home': str(home), 'native_plugin': str(plugin), 'node': node,
                  'cli': str(runtime/'node_modules/@deepseek-ai/dsh/lib/bin.js'), 'port': args.port,
                  'provider': 'deepseek-official', 'model': 'deepseek-flash',
                  'vision_source': 'https://api-docs.deepseek.com/guides/vision/',
                  'environment': {'ACYCLE_BACKEND': 'local', 'ACYCLE_ROOT': str(acycle),
                      'ACYCLE_PYTHON': python, 'ACYCLE_WORKSPACE': str(workspace),
                      'MATLAB_EXECUTABLE': matlab, 'ACYCLE_MATLAB_TIMEOUT': '3600',
                      'ACYCLE_MATLAB_STARTUP_TIMEOUT': '180', 'DSH_HOME': str(home)},
                  'credential_reference': 'DEEPSEEK_API_KEY', 'credentials_stored': False}
    files = {
        profile/'package.json': {'name': 'acycle-private-web-profile', 'private': True,
                                'dsh': {'profile': {'bundles': ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-web-app']}}},
        profile/'cordis.patch.yml': patch,
        directory/'deployment.json': deployment,
    }
    contents = {path: json.dumps(value, ensure_ascii=False, indent=2)+'\n' for path, value in files.items()}
    for path, content in contents.items():
        if path.exists() and path.read_text(encoding='utf-8') != content and not args.force:
            parser.error(f'Refusing to replace changed deployment file {path}; inspect before --force')
    for path, content in contents.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    print(json.dumps({'status': 'generated', 'deployment': str(directory/'deployment.json'),
                      'launch': [python, str(bundle/'local/launch_harness.py'), '--deployment', str(directory/'deployment.json')],
                      'profile': 'web', 'preset': 'acycle', 'harness_version': HARNESS_VERSION,
                      'newark_demo': demo,
                      'credentials_stored': False}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
