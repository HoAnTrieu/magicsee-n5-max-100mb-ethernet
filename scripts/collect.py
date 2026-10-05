#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Collect a reduced, redacted Ethernet report. Does not change network or boot."""
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile


def redact(text):
    text = re.sub(r'(?i)\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b', '[UUID_REDACTED]', text)
    text = re.sub(r'(?i)(?<![0-9a-f:])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![0-9a-f:])', '[MAC_REDACTED]', text)
    text = re.sub(r'(?i)(?<![a-z0-9])(?:[0-9a-f]{1,4}:){2,}[0-9a-f:]*(?:%[a-z0-9_.-]+)?', '[IPV6_REDACTED]', text)
    text = re.sub(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?(?![\d.])', '[IPV4_REDACTED]', text)
    return text


def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return result.stdout + result.stderr + '\nCOMMAND_EXIT_STATUS=' + str(result.returncode) + '\n'
    except (OSError, subprocess.TimeoutExpired) as error:
        return 'COLLECTION_ERROR: ' + str(error) + '\n'


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run: sudo python3 scripts/collect.py')
    os.umask(0o077)
    out = Path(tempfile.mkdtemp(prefix='n5max-public-report-', dir='/tmp'))
    captures = {
        'kernel.txt': os.uname().release + '\n',
        'ethtool.txt': run(['ethtool', 'eth0']),
        'driver.txt': run(['ethtool', '-i', 'eth0']),
        'link-counters.txt': run(['ip', '-s', 'link', 'show', 'dev', 'eth0']),
        'storage.txt': run(['lsblk', '-o', 'NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS']),
        'usb.txt': run(['lsusb']),
    }
    # Separate findmnt calls avoid treating /boot as a source filter.
    captures['mounts.txt'] = run(['findmnt', '-o', 'TARGET,SOURCE,FSTYPE', '/']) + run(['findmnt', '-o', 'TARGET,SOURCE,FSTYPE', '/boot'])
    captures['ethernet-dmesg.txt'] = '\n'.join(line for line in run(['dmesg']).splitlines()
        if re.search(r'eth0|ethernet|dwmac|stmmac|mdio|rgmii|rmii|Cannot attach to PHY', line, re.I)) + '\n'
    summary = {'privacy_mode':'reduced and redacted; review before public upload', 'kernel':os.uname().release}
    net = Path('/sys/class/net/eth0')
    for attr in ('carrier','speed','duplex','operstate'):
        try:
            summary[attr] = (net/attr).read_text().strip()
        except OSError as error:
            summary[attr] = 'unavailable: ' + str(error)
    phy = net/'phydev'
    if phy.is_symlink():
        summary['phy_endpoint'] = phy.resolve().name
        driver = phy/'driver'
        summary['phy_driver'] = driver.resolve().name if driver.is_symlink() else None
        for attr in ('phy_id','phy_interface'):
            try: summary[attr] = (phy/attr).read_text().strip()
            except OSError: summary[attr] = None
    else:
        summary['phy_endpoint'] = None
    dt = Path('/sys/firmware/devicetree/base')
    summary['dt'] = {}
    for relative in (
        'soc/ethernet@ff3f0000/phy-mode',
        'soc/ethernet@ff3f0000/phy-handle',
        'soc/bus@ff600000/mdio-multiplexer@4c000/mdio@0/status',
        'soc/bus@ff600000/mdio-multiplexer@4c000/mdio@1/ethernet-phy@8/compatible',
        'soc/bus@ff600000/mdio-multiplexer@4c000/mdio@1/ethernet-phy@8/reg',
    ):
        path = dt/relative
        if path.is_file():
            data = path.read_bytes()
            summary['dt'][relative] = {'hex':data.hex()}
    captures['summary.json'] = json.dumps(summary, indent=2) + '\n'
    for name, text in captures.items():
        (out/name).write_text(redact(text))
    archive = out.with_suffix('.tar.gz')
    with tarfile.open(archive, 'w:gz') as handle:
        handle.add(out, arcname=out.name)
    if os.environ.get('SUDO_UID','').isdigit() and os.environ.get('SUDO_GID','').isdigit():
        os.chown(archive, int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID']))
    print('Collected: ' + str(archive))
    print('Reduced report: no raw DT, uEnv, IP routes, addresses, SSIDs or credentials collected.')
    print('Review the files before posting publicly; redaction cannot cover every custom log string.')


if __name__ == '__main__':
    main()
