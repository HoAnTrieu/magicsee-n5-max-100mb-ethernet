#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Install the validated DTB; change only FDT and never write the rescue file."""
import argparse
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import secrets
from verify import ROOT, settings, sha256, verify_delta, verify_manifest


@dataclass
class Plan:
    boot: Path
    rescue: Path
    target: Path
    config: Path
    backup: Path
    before: bytes
    after: bytes
    candidate: bytes
    already_installed: bool


def prepare_install(boot, kernel):
    cfg = settings()
    if kernel != cfg['tested_kernel']:
        raise ValueError('Untested kernel: ' + kernel)
    boot = Path(boot)
    rescue = boot / 'dtb/amlogic' / cfg['rescue_name']
    target = boot / 'dtb/amlogic' / cfg['candidate_name']
    config, backup = boot / 'uEnv.txt', boot / 'uEnv.txt.n5max-backup'
    if (boot / 'extlinux/extlinux.conf').exists():
        raise ValueError('Actual extlinux.conf exists; resolve boot selection first')
    for path in (config, backup, target):
        if path.is_symlink():
            raise ValueError('Refusing symlink: ' + str(path))
    if target.exists() and os.path.samefile(target, rescue):
        raise ValueError('Candidate aliases the rescue file')
    base_data = rescue.read_bytes()
    candidate = (ROOT / cfg['candidate']).read_bytes()
    if sha256(base_data) != cfg['base_sha256']:
        raise ValueError('Rescue checksum differs from the tested baseline; no force option')
    if sha256(candidate) != cfg['candidate_sha256']:
        raise ValueError('Release binary checksum mismatch')
    verify_delta(base_data, candidate)
    before = config.read_bytes()
    lines = [line for line in before.splitlines() if line.startswith(b'FDT=')]
    if len(lines) != 1:
        raise ValueError('Expected exactly one active FDT= line')
    old = ('FDT=/dtb/amlogic/' + cfg['rescue_name']).encode()
    new = ('FDT=/dtb/amlogic/' + cfg['candidate_name']).encode()
    if lines[0] == new:
        if not target.is_file() or target.read_bytes() != candidate:
            raise ValueError('FDT selects candidate but installed file differs')
        return Plan(boot, rescue, target, config, backup, before, before, candidate, True)
    if lines[0] != old:
        raise ValueError('Current FDT is not the tested rescue')
    if backup.exists() and backup.read_bytes() != before:
        raise ValueError('Existing backup differs; preserve it and review before installing')
    if target.exists() and target.read_bytes() != candidate:
        raise ValueError('Existing candidate differs; preserve it under another name first')
    # Replace the active complete line, never a commented example above it.
    after = b''.join(new + line[len(old):] if line.rstrip(b'\r\n') == old else line
                     for line in before.splitlines(keepends=True))
    return Plan(boot, rescue, target, config, backup, before, after, candidate, False)


def atomic_write(path, content, mode=0o644):
    temporary = path.parent / (path.name + '.n5max-' + secrets.token_hex(12))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def apply_plan(plan):
    if plan.already_installed:
        return
    # Recheck every condition under the install lock, including aliases and backup.
    fresh = prepare_install(plan.boot, settings()['tested_kernel'])
    if fresh != plan:
        raise ValueError('Boot files changed after planning; nothing selected')
    if not plan.backup.exists():
        fd = os.open(plan.backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(plan.before)
            handle.flush()
            os.fsync(handle.fileno())
    if plan.backup.read_bytes() != plan.before:
        raise ValueError('Backup verification failed')
    atomic_write(plan.target, plan.candidate)
    if plan.target.read_bytes() != plan.candidate:
        raise ValueError('Installed DTB verification failed')
    # uEnv is selected last; partial DTB copy never changes the rescue or FDT.
    atomic_write(plan.config, plan.after, plan.config.stat().st_mode & 0o777)
    os.sync()
    if sha256(plan.rescue.read_bytes()) != settings()['base_sha256']:
        raise ValueError('Rescue checksum unexpectedly changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true', help='Check compatibility without writing')
    mode.add_argument('--apply', action='store_true', help='Install after successful checks; requires root')
    args = parser.parse_args()
    verify_manifest()
    kernel = os.uname().release
    boot = Path('/boot')
    if subprocess.run(['findmnt', '-n', '--mountpoint', str(boot)], capture_output=True).returncode:
        raise ValueError('/boot must be mounted')
    plan = prepare_install(boot, kernel)
    if plan.already_installed:
        print('Already installed: validated DTB selected. No boot file changes needed.')
        return
    print('Kernel: ' + kernel)
    print('Rescue (read only): ' + str(plan.rescue))
    print('Candidate: ' + str(plan.target))
    print('Backup: ' + str(plan.backup))
    print('Only FDT will change; other uEnv bytes are preserved.')
    if args.dry_run:
        print('DRY RUN PASS: nothing written.')
        return
    if os.geteuid() != 0:
        raise ValueError('Run apply with sudo')
    lock = boot / '.n5max-ethernet-install.lock'
    if lock.is_symlink():
        raise ValueError('Refusing symlink install lock')
    lock_fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        apply_plan(plan)
    print('Installed. Rescue retained. Review FDT, connect LAN, then reboot manually.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print('STOP: ' + str(error), file=sys.stderr)
        sys.exit(1)
