# v1.0.0 — Magicsee N5 Max S905X3 Ethernet fix

A community Ethernet fix for the tested ophub Armbian **6.12.111-ophub** setup using the exact X96 Max+ 100M rescue baseline.

The original tree selected external PHY@0/RGMII and failed PHY attach with error -22. The patch selects existing internal PHY@8/RMII and changes only six Ethernet properties. Hardware evidence confirms **100 Mbps Full Duplex, carrier 1 and DHCP** on one S905X3/4 GB Fast Ethernet box. SD/root mount, eMMC visibility, USB enumeration and Wi-Fi were preserved in the captured snapshot.

The ZIP includes complete standalone DTS, tested DTB, exact rescue reference, patch, guarded installer, build/verifier, tests, English/Vietnamese README, evidence and rollback instructions.

Start with README.vi.md or README.md. If already running the tested DTB successfully, retain it; no reinstall is needed. The installer requires the tested kernel and baseline checksum and never overwrites rescue.

Scope: PCB revision unknown, one physical device tested. Not a Gigabit upgrade, official board support declaration, OS image or eMMC protection tool. Exact ophub dtbs_check, other kernels/revisions and long-term stress testing remain unverified. See NOTICE.md for source provenance.
