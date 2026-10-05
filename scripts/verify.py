#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Verify checksums, the Ethernet-only delta, and optional real dtc rebuilds."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from fdt import read_fdt, semantic_diff

ROOT = Path(__file__).resolve().parents[1]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def settings():
    return json.loads((ROOT / 'project.json').read_text())


def verify_manifest():
    for line in (ROOT / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Invalid manifest path: ' + name)
        if sha256(path.read_bytes()) != digest:
            raise ValueError('Checksum mismatch: ' + name)


def verify_delta(base_data, new_data):
    cfg = settings()
    a, reserve_a, cpu_a = read_fdt(base_data)
    b, reserve_b, cpu_b = read_fdt(new_data)
    if set(a) != set(b):
        raise ValueError('Node paths changed')
    actual = semantic_diff(a, b)
    if actual != cfg['expected_changes']:
        raise ValueError('Changes exceed or differ from the six-property Ethernet patch')
    if reserve_a != reserve_b or cpu_a != cpu_b:
        raise ValueError('Memory reservations or boot CPU header changed')
    handles = {}
    for path, props in b.items():
        if 'phandle' in props:
            value = props['phandle']
            if value in handles:
                raise ValueError('Duplicate phandle')
            handles[value] = path
    mac = b['/soc/ethernet@ff3f0000']
    if handles.get(mac['phy-handle']) != '/soc/bus@ff600000/mdio-multiplexer@4c000/mdio@1/ethernet-phy@8':
        raise ValueError('PHY handle does not resolve to internal PHY@8')
    return len(a), len(actual)


def normalized_warnings(text):
    return Counter(re.sub(r'^.*?:\d+\.\d+(?:-\d+(?:\.\d+)?)?: ', '', line)
                   for line in text.splitlines() if 'Warning (' in line)


def compile_source(source, target, dtc):
    process = subprocess.run([dtc, '-I', 'dts', '-O', 'dtb', '-o', str(target), str(source)],
                             capture_output=True, text=True)
    if process.returncode:
        raise ValueError('dtc failed:\n' + process.stderr)
    return process.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, help='Original rescue DTB for semantic verification')
    parser.add_argument('--candidate', type=Path, help='Candidate DTB; defaults to shipped dist file')
    parser.add_argument('--compile', action='store_true', help='Rebuild both sources using real dtc')
    parser.add_argument('--dtc', default='dtc', help='dtc executable name/path')
    parser.add_argument('--output', type=Path, help='Save verified rebuild (requires --compile)')
    args = parser.parse_args()
    if args.output and not args.compile:
        parser.error('--output requires --compile')
    cfg = settings()
    verify_manifest()
    candidate = args.candidate or ROOT / cfg['candidate']
    data = candidate.read_bytes()
    if sha256(data) != cfg['candidate_sha256']:
        raise ValueError('Candidate differs from the validated release binary')
    if sha256((ROOT / cfg['source']).read_bytes()) != cfg['source_sha256']:
        raise ValueError('Source differs from validated release')
    if not args.baseline:
        args.baseline = ROOT / cfg['reference_binary']
    if args.baseline:
        base_data = args.baseline.read_bytes()
        if sha256(base_data) != cfg['base_sha256']:
            raise ValueError('Rescue DTB differs from the tested baseline')
        nodes, changes = verify_delta(base_data, data)
        print(f'PASS: {nodes} nodes preserved; exactly {changes} Ethernet property changes')
    if args.compile:
        if not shutil.which(args.dtc):
            raise ValueError('dtc not found; install device-tree-compiler')
        with tempfile.TemporaryDirectory(prefix='n5max-build-') as temp:
            temp = Path(temp)
            baseline_log = compile_source(ROOT / cfg['reference_source'], temp / 'base.dtb', args.dtc)
            patched_log = compile_source(ROOT / cfg['source'], temp / 'patched.dtb', args.dtc)
            base_data, rebuilt = (temp / 'base.dtb').read_bytes(), (temp / 'patched.dtb').read_bytes()
            if read_fdt(base_data) != read_fdt((ROOT / cfg['reference_binary']).read_bytes()):
                raise ValueError('Rebuilt baseline differs from original rescue tree')
            nodes, changes = verify_delta(base_data, rebuilt)
            if read_fdt(rebuilt) != read_fdt(data):
                raise ValueError('Rebuilt tree differs from validated binary')
            added = normalized_warnings(patched_log) - normalized_warnings(baseline_log)
            if added:
                raise ValueError('New dtc warnings: ' + repr(dict(added)))
            print(f'PASS: real dtc rebuild; {nodes} nodes, {changes} changes; no new warnings')
            print(f'Warnings baseline/patched: {sum(normalized_warnings(baseline_log).values())}/{sum(normalized_warnings(patched_log).values())}')
            if args.output:
                target = args.output.resolve()
                if target.is_relative_to(Path('/boot')) or target == (ROOT / cfg['candidate']).resolve():
                    raise ValueError('Build output must not overwrite /boot or the validated release binary')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(rebuilt)
                target.with_suffix('.dtc.log').write_text(patched_log)
                print('Saved verified rebuild: ' + str(target))
    print('PASS: release checksums. Hardware results are recorded evidence, not a CI test.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        sys.exit(1)
