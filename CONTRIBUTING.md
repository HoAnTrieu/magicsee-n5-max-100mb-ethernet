# Contributing

This fix is verified on one S905X3 Fast Ethernet device. Additional PCB/kernel combinations require their own evidence; matching enclosure names are insufficient.

For a report, include SoC, RAM, PCB revision if available, exact kernel, rescue checksum, runtime phy-mode, PHY endpoint/driver, negotiated speed/duplex/carrier, ping bound to eth0, throughput direction and duration, and storage/USB/Wi-Fi observations. Use `sudo python3 scripts/collect.py`, review the reduced report, and omit private identifiers. See [privacy](docs/PRIVACY.md).

For code changes, preserve the rescue, backup and single active FDT behavior. Use real dtc, compare full node/property bytes and memory reservations, and run:

```bash
python3 scripts/verify.py
bash scripts/build.sh
python3 -m unittest discover -s tests -v
```

Do not mask dtc warnings, substitute a mock DTB, blindly copy vendor clock/GPIO IDs, or claim a board test from CI alone. Propose a separate compatibility target when the baseline/kernel differs; do not remove existing guards to claim wider support.

Record hardware results and uncertainties separately. Keep matching source with any distributed DTB and preserve upstream notices and licensing.
