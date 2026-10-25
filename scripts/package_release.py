#!/usr/bin/env python3
"""Build wheel, native Harness package and a clean, inspectable source bundle."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.2.0'


def main():
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    shutil.copytree(ROOT/'skills', ROOT/'plugin'/'skills', dirs_exist_ok=True)
    shutil.copyfile(ROOT/'LICENSE', ROOT/'plugin'/'LICENSE')
    subprocess.run([sys.executable, '-m', 'build'], cwd=ROOT, check=True)
    subprocess.run(['npm','pack','--pack-destination',str(dist)], cwd=ROOT/'plugin', check=True)
    artifacts = [*dist.glob('*.whl'),*dist.glob('*.tar.gz'),*dist.glob('*.tgz')]
    hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}
    (dist/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n')
    archive = dist/f'acycle-deepseek-{VERSION}-bundle.zip'
    source_dirs = ['src','matlab','skills','plugin','scripts','tests','docs','examples','benchmarks','.github']
    source_files = ['README.md','LICENSE','pyproject.toml','setup.py','MANIFEST.in','.gitignore']
    paths = [ROOT/name for name in source_files]
    for name in source_dirs:
        paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and not any(part in {'node_modules','__pycache__','.pytest_cache'} for part in p.parts))
    # Include reviewable receipts and reports, but not large downloaded CI caches.
    paths.extend(p for p in (ROOT/'validation').glob('*') if p.is_file())
    paths.extend(p for p in (ROOT/'validation'/'live-runs').rglob('*') if p.is_file())
    paths.extend(artifacts+[dist/'SHA256SUMS.json'])
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as output:
        for p in sorted(set(paths)):
            if p.exists():
                output.write(p,Path('acycle-deepseek')/p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as check:
        assert check.testzip() is None
    print(json.dumps({'bundle':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'packages':hashes},indent=2))


if __name__ == '__main__':
    main()
