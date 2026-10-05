---
name: Ethernet problem
about: Report a boot, PHY, link or deployment failure
---

## Device
- SoC / RAM:
- PCB revision (if known):
- Exact kernel (`uname -r`):
- Rescue filename / SHA-256:
- Boot medium / layout:

## Failure
- Installer output or failing command:
- Runtime phy-mode / phydev endpoint:
- ethtool link / speed / duplex / carrier:
- Can you recover by selecting rescue?

## Evidence
Attach a reviewed reduced report from `sudo python3 scripts/collect.py`.
Remove private IP/MAC/UUID/serial information; do not attach raw runtime DTS or original debug archives.
