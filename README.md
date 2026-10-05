# Magicsee N5 Max S905X3 Ethernet fix for Armbian

[Tiếng Việt](README.vi.md) · [Technical analysis, Vietnamese](docs/TECHNICAL_ANALYSIS.md) · [Hardware evidence](docs/VALIDATION.md) · [Rollback](docs/ROLLBACK.md) · [Bonus: eMMC guard](BONUS/README-eMMC-GUARD.md)

**Verified on one Magicsee N5 Max S905X3: internal PHY attached, RMII, 100 Mbps Full Duplex, carrier 1 and DHCP.** This project preserves the working X96 Max+ 100M boot configuration and changes only six Ethernet properties. Long-term stability and interface-bound bidirectional throughput have not been measured. A later user-reported transfer estimate is recorded separately in validation.

This is a community board-specific fix, not an official Armbian support declaration. N5 Max enclosures have been sold with different hardware; the S905X2 model and other PCB revisions are outside the tested scope.

## Tested configuration

| Item | Value |
|---|---|
| Box / SoC | Magicsee N5 Max / Amlogic S905X3 (SM1) |
| RAM class | 4 GB; Linux reports about 3.24 GiB usable |
| PCB revision | Not recorded |
| OS | ophub Armbian v26.11.0, Ubuntu Noble |
| Kernel | **6.12.111-ophub** |
| Original working boot DTB | `meson-sm1-x96-max-plus-100m.dtb` |
| PHY selected by the fix | Meson G12A Internal PHY, mux branch 1, address 8 |
| MAC–PHY mode | **RMII** |
| Measured link | **100 Mbps / Full Duplex / autoneg on** |
| Basic regression | SD/root mounted, eMMC visible, USB enumeration unchanged, Wi-Fi still connected |

The installer requires the exact tested kernel and rescue DTB checksum. A matching model name alone is not enough to bypass these checks. Hardware confirmation comes from the supplied device logs; CI checks source/build/install safety, not a physical board.

## What it fixes

Before:

```text
validation of rgmii ... 00006280 failed: -EINVAL
__stmmac_open: Cannot attach to PHY (error: -22)
```

The baseline selects external MDIO branch 0, PHY@0 and RGMII. Its `100m` filename limits external PHY speed; it does not select the integrated PHY. The selected external endpoint reports ID 0 and no usable speed capabilities.

After:

```text
PHY [mdio_mux-0.1:08] driver [Meson G12A Internal PHY] (irq=25)
configuring for phy/rmii link mode
Link is Up - 100Mbps/Full - flow control rx/tx
```

The successful internal PHY link confirms the functional LAN path on the tested device. See [validation](docs/VALIDATION.md) for what was and was not measured.

## Quick deployment: download, run one script, reboot manually

Start from a box that already boots with the tested rescue DTB and **6.12.111-ophub** kernel. The script handles release/kernel checks, backup, copying the new DTB and changing only FDT. Keep SD recovery access available.

```bash
git clone https://github.com/HoAnTrieu/magicsee-n5-max-100mb-ethernet.git
cd magicsee-n5-max-100mb-ethernet
sudo bash install.sh
```

If Git is missing: `sudo apt-get update && sudo apt-get install git`.

Alternatively, extract the ZIP and upload the whole project folder to your Armbian home using MobaXterm SFTP:

```bash
cd ~/magicsee-n5-max-ethernet
sudo bash install.sh
```

Only after the script reports success, connect LAN and reboot manually:

```bash
sudo reboot
```

For a read-only preview: `sudo bash install.sh --dry-run`.

`install.sh` delegates boot-file changes to the guarded Python installer. Beginners do not need to run the Python files separately. It retains rescue, backs up uEnv and selects `/dtb/amlogic/meson-sm1-magicsee-n5-max.dtb` without automatic reboot. If already selected with the correct binary, no changes are made.

An untested kernel/baseline, active extlinux.conf, conflicting backup/candidate or invalid FDT selection stops installation. There is no force option. See [deployment details](docs/DEPLOYMENT.md) for guards and the lower-level commands.

## Check after reboot

Connect LAN to a working switch/router. Through Wi-Fi SSH or console:

```bash
uname -r
sudo ip link set dev eth0 up
sleep 3
sudo ethtool eth0
sudo ethtool -i eth0
cat /sys/class/net/eth0/carrier
cat /sys/class/net/eth0/speed
ip -br link
ip -br addr
sudo dmesg | grep -Ei 'eth0|ethernet|dwmac|stmmac|phy|mdio|rgmii|rmii'
lsblk
findmnt /
lsusb
```

Success means PHY@8 attached, RMII in MAC logs/runtime, link yes, speed 100, full duplex and carrier 1. The preserved root `model` still says AMedia X96 Max+; that cosmetic string is not an indication that the old Ethernet configuration was loaded.

Only after link succeeds, check DHCP and ping through `eth0`. Use your actual Ethernet gateway:

```bash
ip -4 route show default dev eth0
ping -I eth0 -c 20 YOUR_ETHERNET_GATEWAY_IP
ip -s link show dev eth0
```

[Testing](docs/TESTING.md) includes native Windows `ping.exe`/`curl.exe`, a RAM-backed HTTP throughput estimate and optional Linux iperf3. Wi-Fi success must not be mistaken for an Ethernet test.

## Rollback

If the system boots:

```bash
sudo cp /boot/uEnv.txt.n5max-backup /boot/uEnv.txt
grep '^FDT=' /boot/uEnv.txt
sudo sync
sudo reboot
```

If it does not boot, power off, remove the SD card and open its FAT **BOOT** partition on a PC. Restore `uEnv.txt.n5max-backup`, or change only FDT in the root `uEnv.txt` back to:

```text
FDT=/dtb/amlogic/meson-sm1-x96-max-plus-100m.dtb
```

Keep root UUID, APPEND, LINUX and INITRD unchanged. [Full rollback procedure](docs/ROLLBACK.md).

## Bonus (optional): eMMC read-only guard

`BONUS/` is an extra, unrelated to the Ethernet fix, for boxes that boot Armbian from SD and must keep the internal eMMC untouched:

| File | Purpose |
|---|---|
| `BONUS/lock-emmc.sh` | Set the eMMC block device read-only, re-arm it after every boot through a systemd service and a udev rule, and block the usual `armbian-install` path |
| `BONUS/unlock-emmc.sh` | Remove everything the lock created and return the eMMC to read-write |
| `BONUS/README-eMMC-GUARD.md` | Full walkthrough (Vietnamese): safety checks, verification after reboot, cheat sheet and what the guard does **not** do |
| `BONUS/LOG_OF_N5_MAX_BENCH.txt` | CPU/storage benchmark log from the tested box |

Nothing in this project needs the bonus, and `install.sh` never runs it. It is a **reversible software lock**, not hardware write-protect: it does not format, does not touch the firmware or bootloader, and it refuses to run when `/` or `/boot` already lives on the eMMC. Read the BONUS README first and confirm your device names yourself:

```bash
lsblk -o NAME,SIZE,RO,TYPE,FSTYPE,MOUNTPOINTS
sudo ./BONUS/lock-emmc.sh --apply     # type the requested confirmation exactly
sudo blockdev --getro /dev/mmcblk2     # 1 = locked
```

Use `sudo ./BONUS/unlock-emmc.sh --remove` to undo it. Do not run the lock on a machine whose OS runs from eMMC.

## Build and verify

On Ubuntu/Debian, install tools, then build:

```bash
sudo apt-get update
sudo apt-get install device-tree-compiler python3
bash scripts/build.sh
python3 -m unittest discover -s tests -v
```

`build/` contains the verified rebuild and dtc log. The validated `dist/` binary is not overwritten. Direct compile is also possible:

```bash
mkdir -p build
dtc -I dts -O dtb -o build/meson-sm1-magicsee-n5-max.dtb src/meson-sm1-magicsee-n5-max.dts
```

The release was built with **dtc 1.7.0**. The baseline rebuild with that version exactly reproduces its original binary. Both standalone decompiled sources have 285 inherited warnings; the fix adds none. The verifier compares node paths, raw property bytes, phandles, reservation entries and boot CPU header. It rejects any delta beyond the six allowed Ethernet properties.

`dtbs_check` against the exact ophub source was **not run**: its source commit and matching binding set were not available. Successful compilation is not schema certification. Source provenance and limitations are documented in [NOTICE](NOTICE.md) and [technical analysis](docs/TECHNICAL_ANALYSIS.md).

## Project layout

| Path | Purpose |
|---|---|
| `src/` | Complete standalone patched DTS |
| `dist/` | Exact hardware-tested compiled DTB |
| `reference/` | Exact rescue DTS/DTB for comparison; not installation payloads |
| `patches/` | Two-hunk Ethernet-only diff |
| `install.sh` | One-command beginner install; reports when to reboot manually |
| `BONUS/` | Optional eMMC read-only guard scripts and their guide |
| `scripts/` | Real dtc build, semantic verifier, guarded installer, reduced collector and release packager |
| `tests/` | Disposable boot fixtures testing rescue/backup/config protection |
| `evidence/` | Redacted hardware excerpts and build results |
| `docs/` | Deployment, analysis, validation, tests, rollback, privacy and publishing |
| `.github/` | CI and community issue templates |

## Checksums

| Artifact | SHA-256 |
|---|---|
| Rescue DTB | `386cdd6714f2e507db8b443c263c1a7d5fb7facc24bce9c8b2208d8bfe5c67eb` |
| Tested fix DTB | `03c8877650e9b7d7feda656db775dcd591ba20f6528665c2367537c8888fbffd` |

`SHA256SUMS` covers the public project files, including `BONUS/`. Checksums detect changed files; they are not a signature or a guarantee of hardware compatibility.

## Contributing and publishing

For a new board revision, provide a [reduced report](docs/PRIVACY.md), baseline checksum, exact kernel and actual link result. Do not substitute whole vendor/CoreELEC DTBs or port numeric phandles/clock IDs blindly. See [CONTRIBUTING](CONTRIBUTING.md).

This project lives at [github.com/HoAnTrieu/magicsee-n5-max-100mb-ethernet](https://github.com/HoAnTrieu/magicsee-n5-max-100mb-ethernet). The v1.0.1 tag, release text from [RELEASE_NOTES](docs/RELEASE_NOTES.md) and the GitHub web/Git steps are described in [PUBLISHING](docs/PUBLISHING.md). Run `python3 scripts/package.py` to regenerate the manifest and archive after verification.

New project code/documentation is GPL-2.0-only. Inherited Linux Device Tree content retains its upstream terms; exact upstream source notices could not be recovered from the decompiled baseline; see [LICENSE](LICENSE), [NOTICE](NOTICE.md) and [sources](docs/SOURCES.md).
