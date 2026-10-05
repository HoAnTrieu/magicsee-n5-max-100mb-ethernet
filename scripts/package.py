#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Update public manifest, verify release and create a source+binary ZIP."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIRS = {'src', 'dist', 'reference', 'patches', 'scripts', 'tests', 'docs', 'evidence', '.github'}
PUBLIC_ROOT = {'README.md', 'README.vi.md', 'LICENSE', 'NOTICE.md', 'CHANGELOG.md',
               'CONTRIBUTING.md', 'project.json', '.gitignore', '.gitattributes'}


def public_files():
    result = []
    for path in ROOT.rglob('*'):
        relative = path.relative_to(ROOT)
        if not path.is_file() or '__pycache__' in relative.parts:
            continue
        if path.suffix in {'.pyc', '.pyo'}:
            continue
        if len(relative.parts) == 1:
            if path.name not in PUBLIC_ROOT:
                continue
        elif relative.parts[0] not in PUBLIC_DIRS:
            continue
        if path.is_symlink():
            raise ValueError('Symlink cannot be packaged: ' + str(relative))
        result.append(path)
    return sorted(result, key=lambda f: f.relative_to(ROOT).as_posix())


def main():
    cfg = json.loads((ROOT/'project.json').read_text())
    if cfg['name'] != 'magicsee-n5-max-ethernet':
        raise ValueError('Unexpected project name')
    # These are declared tested hashes, not automatically rebaselined by packaging.
    for name, key in [('candidate', 'candidate_sha256'), ('reference_binary', 'base_sha256'),
                      ('source', 'source_sha256')]:
        if hashlib.sha256((ROOT/cfg[name]).read_bytes()).hexdigest() != cfg[key]:
            raise ValueError('Tested payload changed; review evidence before release: ' + name)
    files = public_files()
    manifest = ROOT/'SHA256SUMS'
    manifest.write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+
                              f.relative_to(ROOT).as_posix()+'\n' for f in files))
    subprocess.run([sys.executable, 'scripts/verify.py'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                   cwd=ROOT, check=True)
    # The real dtc rebuild is a separate required release step: bash scripts/build.sh.
    out = ROOT/'release'; out.mkdir(exist_ok=True)
    archive = out/(cfg['name']+'-v'+cfg['version']+'.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(files+[manifest], key=lambda f:f.relative_to(ROOT).as_posix()):
            info = zipfile.ZipInfo(cfg['name']+'/'+f.relative_to(ROOT).as_posix(), (2026,10,5,0,0,0))
            info.create_system = 3
            info.external_attr = (0o100644 << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())
    checksum = archive.with_suffix('.zip.sha256')
    checksum.write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print('Created: '+str(archive))
    print('Archive checksum: '+str(checksum))


if __name__ == '__main__':
    main()
