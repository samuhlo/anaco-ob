#!/usr/bin/env python3
"""Build AMO reviewer sources from version-controlled files, never local profiles."""
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / 'extension/manifest.json').read_text())['version']
target = ROOT / 'dist' / f'anaco-ob-{version}-sources.zip'
target.parent.mkdir(exist_ok=True)
allowed_dirs = {'extension', 'native', 'anaco_ob', 'scripts', 'tests', 'skills', 'docs', '.github'}
allowed_files = {'package.json', 'package-lock.json', 'pyproject.toml', 'README.md', 'LICENSE', 'PRIVACY.md', 'AMO_BUILD.md'}
files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name in sorted(filter(None, files)):
        path = Path(name)
        if path.parts[0] not in allowed_dirs and name not in allowed_files:
            continue
        source = ROOT / path
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f'Unexpected release input: {name}')
        info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (0o755 if source.stat().st_mode & 0o111 else 0o644) << 16
        archive.writestr(info, source.read_bytes())
print(target)
