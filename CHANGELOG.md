# Changelog

## 1.0.0 — 2026-10-05

- Fix the tested N5 Max S905X3 LAN path by selecting internal PHY@8 and RMII, disabling the external MDIO branch and dropping external pinctrl/RGMII delay references.
- Preserve the working rescue tree, all 542 nodes and 2,300 unchanged properties.
- Ship the exact DTB confirmed to attach the internal PHY and negotiate 100 Mbps Full Duplex with DHCP on one device.
- Add guarded installer with dry-run, semantic verification, real dtc build, installation safety tests and reduced diagnostic collector.
- Add English/Vietnamese READMEs, deployment/test/rollback/research evidence, community templates and CI.
- Record limitations: exact ophub dtbs_check and source commit unavailable; no long-term stability or other-revision validation.

The DTB binary has not changed since the successful hardware test. Packaging completion fixes active FDT replacement when a commented FDT example precedes it; only installer code and documentation changed.
