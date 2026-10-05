#!/usr/bin/env bash
# unlock-emmc.sh
# Reverses the software protection installed by lock-emmc.sh.
#
# IMPORTANT:
# - This does NOT touch eMMC permanent/hardware write-protect bits.
# - It only removes the systemd/udev/command guards created by lock-emmc.sh
#   and returns the eMMC user area to normal read-write mode.
# - For safety, this script refuses to guess the eMMC device. It reads the
#   target saved by lock-emmc.sh in /etc/emmc-guard/config.

set -Eeuo pipefail

MODE="${1:-}"
CONFIG="/etc/emmc-guard/config"

die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }

[[ "${EUID}" -eq 0 ]] || die "Run as root: sudo bash $0 --remove"

[[ "$MODE" == "--remove" ]] || {
  cat <<EOF
Usage:
  sudo bash $0 --remove

This script only removes protection previously installed by lock-emmc.sh.
EOF
  exit 2
}

[[ -f "$CONFIG" ]] || die \
"Missing $CONFIG. Refusing to guess which disk is the protected eMMC."

TARGET="$(sed -n 's/^EMMC_DEVICE=//p' "$CONFIG" | head -n1 | tr -d '\r\n')"
NAME="$(sed -n 's/^EMMC_NAME=//p' "$CONFIG" | head -n1 | tr -d '\r\n')"

[[ -n "$TARGET" ]] || die "EMMC_DEVICE is missing from $CONFIG."
[[ -n "$NAME" ]] || NAME="${TARGET##*/}"

[[ "$TARGET" == "/dev/$NAME" ]] || die \
"Config mismatch: EMMC_DEVICE=$TARGET but EMMC_NAME=$NAME."

[[ "$NAME" =~ ^mmcblk[0-9]+$ ]] || die "Unexpected MMC device name: $NAME."
[[ "$TARGET" == /dev/mmcblk* ]] || die "Refusing non-MMC target: $TARGET."
[[ -b "$TARGET" ]] || die "$TARGET is not currently a block device."
[[ -d "/sys/block/$NAME" ]] || die "Missing /sys/block/$NAME."

MMC_TYPE="$(cat "/sys/block/$NAME/device/type" 2>/dev/null | tr -d '\r\n' || true)"
[[ "$MMC_TYPE" == "MMC" ]] || die \
"$TARGET reports type '$MMC_TYPE', not 'MMC'. Refusing."

[[ -b "/dev/${NAME}boot0" && -b "/dev/${NAME}boot1" ]] || die \
"$TARGET no longer exposes boot0/boot1. Refusing automatic unlock."

SIZE="$(lsblk -dnro SIZE "$TARGET" 2>/dev/null || echo '?')"
MODEL="$(cat "/sys/block/$NAME/device/name" 2>/dev/null | tr -d '\r\n' || true)"
CID="$(cat "/sys/block/$NAME/device/cid" 2>/dev/null | tr -d '\r\n' || true)"
RO_BEFORE="$(blockdev --getro "$TARGET" 2>/dev/null || echo '?')"

cat <<EOF

=== eMMC SOFTWARE UNLOCK ===
Target      : $TARGET
Type        : $MMC_TYPE
Size        : $SIZE
Model/name  : ${MODEL:-unknown}
CID         : ${CID:-unknown}
Current RO  : $RO_BEFORE

This will remove ONLY the reversible software guard created by lock-emmc.sh:
  - disable/remove emmc-guard.service
  - remove the eMMC udev read-only rule
  - remove the blocking armbian-install wrapper
  - remove the login warning and guard config
  - return the eMMC user area/partitions to read-write mode

It will NOT modify permanent eMMC hardware write-protect bits.

EOF

read -r -p "Type exactly 'UNLOCK $NAME' to continue: " CONFIRM
[[ "$CONFIRM" == "UNLOCK $NAME" ]] || die \
"Confirmation did not match. Nothing changed."

# Stop the boot-time guard first.
if systemctl list-unit-files 2>/dev/null | grep -q '^emmc-guard\.service'; then
    systemctl disable --now emmc-guard.service >/dev/null 2>&1 || true
else
    systemctl stop emmc-guard.service >/dev/null 2>&1 || true
fi

# Remove the udev rule BEFORE changing block-device state so it cannot
# immediately re-apply the read-only flag on a later device event.
rm -f /etc/udev/rules.d/99-emmc-readonly.rules
udevadm control --reload-rules 2>/dev/null || true
udevadm settle 2>/dev/null || true

# Remove the systemd unit and guard executable.
rm -f /etc/systemd/system/emmc-guard.service
rm -f /usr/local/sbin/emmc-guard

systemctl daemon-reload
systemctl reset-failed emmc-guard.service >/dev/null 2>&1 || true

# Remove only the armbian-install blocker created by lock-emmc.sh.
if [[ -f /usr/local/sbin/armbian-install ]] && \
   grep -q "BLOCKED: armbian-install is intentionally disabled on this machine." \
   /usr/local/sbin/armbian-install 2>/dev/null; then
    rm -f /usr/local/sbin/armbian-install
else
    [[ ! -e /usr/local/sbin/armbian-install ]] || \
      warn "/usr/local/sbin/armbian-install does not look like our blocker; left untouched."
fi

if [[ -L /usr/local/bin/armbian-install ]]; then
    LINK_TARGET="$(readlink -f /usr/local/bin/armbian-install 2>/dev/null || true)"
    if [[ "$LINK_TARGET" == "/usr/local/sbin/armbian-install" || \
          ! -e /usr/local/sbin/armbian-install ]]; then
        rm -f /usr/local/bin/armbian-install
    fi
fi

rm -f /etc/profile.d/99-emmc-protected.sh

# Return eMMC user area and normal partitions to read-write.
BLOCKDEV="$(command -v blockdev || true)"
[[ -x "$BLOCKDEV" ]] || die "blockdev command not found."

"$BLOCKDEV" --setrw "$TARGET"

for node in "${TARGET}"p*; do
    [[ -b "$node" ]] || continue
    "$BLOCKDEV" --setrw "$node" 2>/dev/null || \
      warn "Could not set $node read-write immediately."
done

# boot0/boot1 often have their own kernel force_ro policy. We do not alter
# that policy here. The lock script never changed permanent HW protection.
# Best-effort clear only the temporary blockdev RO flag if the kernel permits.
for node in "${TARGET}boot0" "${TARGET}boot1" "${TARGET}rpmb"; do
    [[ -b "$node" ]] || continue
    "$BLOCKDEV" --setrw "$node" 2>/dev/null || true
done

RO_AFTER="$("$BLOCKDEV" --getro "$TARGET" 2>/dev/null || echo '?')"

if [[ "$RO_AFTER" != "0" ]]; then
    die "Software guard files were removed, but $TARGET still reports read-only=$RO_AFTER."
fi

# Remove config last so an interrupted run still remembers which device was protected.
rm -rf /etc/emmc-guard

hash -r 2>/dev/null || true

echo
echo "=== eMMC SOFTWARE PROTECTION REMOVED ==="
echo "Read-only state:"
lsblk -o NAME,SIZE,RO,TYPE,MOUNTPOINTS "$TARGET" 2>/dev/null || true
echo
echo "blockdev --getro $TARGET => $RO_AFTER"
echo
echo "armbian-install now resolves to:"
command -v armbian-install 2>/dev/null || echo "(not found in PATH)"
echo
echo "No permanent eMMC write-protect bits were changed."
echo "A reboot is recommended, then verify:"
echo "  sudo blockdev --getro $TARGET"
echo "  lsblk -o NAME,SIZE,RO,TYPE,MOUNTPOINTS"
echo "  command -v armbian-install"
