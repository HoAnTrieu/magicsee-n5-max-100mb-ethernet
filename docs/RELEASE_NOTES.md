# v1.0.1 — Magicsee N5 Max S905X3 Ethernet fix

A community Ethernet fix for the tested ophub Armbian **6.12.111-ophub** setup using the exact X96 Max+ 100M rescue baseline.

The original tree selected external PHY@0/RGMII and failed PHY attach with error -22. The patch selects existing internal PHY@8/RMII and changes only six Ethernet properties. Hardware evidence confirms **100 Mbps Full Duplex, carrier 1 and DHCP** on one S905X3/4 GB Fast Ethernet box. SD/root mount, eMMC visibility, USB enumeration and Wi-Fi were preserved in the captured snapshot.

The ZIP includes complete standalone DTS, tested DTB, exact rescue reference, patch, guarded installer, build/verifier, tests, English/Vietnamese README, evidence and rollback instructions.

Start with README.vi.md or README.md. Beginner installation is now `sudo bash install.sh`; the script reports when to reboot manually. The README clone link points to the real repository, `https://github.com/HoAnTrieu/magicsee-n5-max-100mb-ethernet`, so newcomers can copy the command directly. If already running the tested DTB successfully, retain it; no reinstall is needed. The installer requires the tested kernel and baseline checksum and never overwrites rescue.

Also new: the optional `BONUS/` eMMC read-only guard — `lock-emmc.sh`, `unlock-emmc.sh`, their guide and the benchmark log — is documented in both READMEs and now ships inside the ZIP. It is unrelated to the Ethernet fix, is never run by `install.sh`, and stays a reversible software lock.

Scope: PCB revision unknown, one physical device tested. Not a Gigabit upgrade, official board support declaration, OS image or eMMC protection tool. Exact ophub dtbs_check, other kernels/revisions and long-term stress testing remain unverified. See NOTICE.md for source provenance.
