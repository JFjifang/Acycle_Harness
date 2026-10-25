#!/usr/bin/env python3
"""Build wheel, native Harness package and a clean, inspectable source bundle."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.3.0'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle-only', action='store_true', help='Reassemble evidence without rebuilding verified packages')
    args = parser.parse_args()
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    shutil.copytree(ROOT/'skills', ROOT/'plugin'/'skills', dirs_exist_ok=True)
    shutil.copyfile(ROOT/'LICENSE', ROOT/'plugin'/'LICENSE')
    if not args.bundle_only:
        subprocess.run([sys.executable, '-m', 'build'], cwd=ROOT, check=True)
        with tempfile.TemporaryDirectory(prefix='acycle-npm-') as cache:
            subprocess.run(['npm','pack','--cache',cache,'--pack-destination',str(dist)], cwd=ROOT/'plugin', check=True)
    artifacts = [*dist.glob(f'*{VERSION}*.whl'),*dist.glob(f'*{VERSION}*.tar.gz'),*dist.glob(f'*{VERSION}*.tgz')]
    hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}
    (dist/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n')
    archive = dist/f'acycle-deepseek-{VERSION}-bundle.zip'
    source_dirs = ['src','matlab','skills','plugin','scripts','tests','docs','examples','benchmarks','local','.github']
    source_files = ['README.md','LICENSE','pyproject.toml','setup.py','MANIFEST.in','.gitignore']
    paths = [ROOT/name for name in source_files]
    for name in source_dirs:
        paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and not any(part in {'node_modules','__pycache__','.pytest_cache','generated'} for part in p.parts))
    # Include selected research evidence, not transport caches or credentials.
    paths.extend(p for p in (ROOT/'validation').glob('*') if p.is_file())
    for evidence in ['v0.2','live-runs','live-runs-v03','artifacts/newark','artifacts/expanded-first','artifacts/expanded-final','artifacts/expanded-release']:
        paths.extend(p for p in (ROOT/'validation'/evidence).rglob('*') if p.is_file())
    paths.extend(artifacts+[dist/'SHA256SUMS.json'])
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as output:
        for p in sorted(set(paths)):
            if p.exists():
                output.write(p,Path('acycle-deepseek')/p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as check:
        assert check.testzip() is None
    handoff = dist/f'acycle-local-handoff-{VERSION}.zip'
    # A separate self-contained deployment kit includes source, wheels, tools,
    # guides and extracted CSV fixtures; publisher archives and historical
    # cloud run outputs remain in the full research bundle.
    with zipfile.ZipFile(handoff,'w',compression=zipfile.ZIP_DEFLATED) as output:
        for p in sorted(set(paths)):
            if not p.exists():
                continue
            relative=p.relative_to(ROOT)
            if relative.parts[0]=='validation' and (len(relative.parts)!=2 or relative.name not in {
                'ACCEPTANCE.md','NEWARK.md','matlab-summary.json','release-verification.json',
                'native-plugin-smoke.json','python-tests.txt','node-tests.txt','paper-validation.json','local-handoff-checks.json','local-bundle-check.json','local-config-fix.json'}):
                continue
            if relative.parts[:2]==('benchmarks','sources') and p.suffix not in {'.json','.txt'}:
                continue
            output.write(p,Path('acycle-deepseek')/relative)
    with zipfile.ZipFile(handoff) as check:
        assert check.testzip() is None
    print(json.dumps({'bundle':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                      'local_handoff':str(handoff),'handoff_bytes':handoff.stat().st_size,'packages':hashes},indent=2))


if __name__ == '__main__':
    main()
