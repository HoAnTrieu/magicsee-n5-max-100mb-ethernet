#!/usr/bin/env bash
# lock-emmc.sh
# Protect the internal eMMC of an Armbian TV box from accidental writes/installation.
# Default target is /dev/mmcblk2. Override only if you KNOW the internal eMMC is different:
#   sudo EMMC_DEVICE=/dev/mmcblkX bash lock-emmc.sh --apply
#
# This is a practical software guard, not an irreversible hardware write-protect.
# A user with full root access can intentionally remove/bypass it.

set -Eeuo pipefail

TARGET="${EMMC_DEVICE:-/dev/mmcblk2}"
NAME="${TARGET##*/}"
MODE="${1:-}"

die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }

[[ "${EUID}" -eq 0 ]] || die "Run as root: sudo bash $0 --apply"
[[ "$MODE" == "--apply" ]] || {
  cat <<EOF
Usage:
  sudo bash $0 --apply

Optional override, ONLY if the internal eMMC is not /dev/mmcblk2:
  sudo EMMC_DEVICE=/dev/mmcblkX bash $0 --apply
EOF
  exit 2
}

[[ "$TARGET" == /dev/mmcblk* ]] || die "Refusing non-MMC target: $TARGET"
[[ "$NAME" =~ ^mmcblk[0-9]+$ ]] || die "Unexpected MMC device name: $NAME"
[[ -b "$TARGET" ]] || die "$TARGET is not a block device."
[[ -d "/sys/block/$NAME" ]] || die "Missing /sys/block/$NAME."

# eMMC normally reports type MMC and exposes boot0/boot1 hardware boot areas.
MMC_TYPE="$(cat "/sys/block/$NAME/device/type" 2>/dev/null | tr -d '\r\n' || true)"
[[ "$MMC_TYPE" == "MMC" ]] || die "$TARGET reports type '$MMC_TYPE', not 'MMC'. Refusing."
[[ -b "/dev/${NAME}boot0" && -b "/dev/${NAME}boot1" ]] || \
  die "$TARGET does not expose boot0/boot1. It may not be the internal eMMC. Refusing."

ROOT_SRC="$(findmnt -nro SOURCE / 2>/dev/null || true)"
BOOT_SRC="$(findmnt -nro SOURCE /boot 2>/dev/null || true)"

resolve_dev() {
  local d="${1:-}"
  [[ -n "$d" ]] || return 0
  readlink -f "$d" 2>/dev/null || printf '%s\n' "$d"
}

belongs_to_target() {
  local src resolved parent
  src="${1:-}"
  [[ -n "$src" ]] || return 1
  resolved="$(resolve_dev "$src")"
  [[ "$resolved" == "$TARGET" || "$resolved" == "${TARGET}p"* ]] && return 0
  if [[ -b "$resolved" ]]; then
    parent="$(lsblk -ndo PKNAME "$resolved" 2>/dev/null | head -n1 | tr -d '[:space:]' || true)"
    [[ "$parent" == "$NAME" ]] && return 0
  fi
  return 1
}

belongs_to_target "$ROOT_SRC" && die "Root filesystem is on $TARGET. Refusing to lock the active root disk."
belongs_to_target "$BOOT_SRC" && die "/boot is on $TARGET. Refusing to lock the active boot disk."

# Refuse if any eMMC partition is currently mounted.
while IFS= read -r line; do
  dev="${line%% *}"
  mnt="${line#* }"
  [[ "$dev" == "$mnt" ]] && mnt=""
  if [[ -n "${mnt// }" ]]; then
    die "$dev is mounted at $mnt. Unmount it before enabling the guard."
  fi
done < <(lsblk -nrpo NAME,MOUNTPOINT "$TARGET" 2>/dev/null || true)

# Refuse if swap lives on the target.
if command -v swapon >/dev/null 2>&1; then
  while IFS= read -r swapdev; do
    [[ -n "$swapdev" ]] || continue
    belongs_to_target "$swapdev" && die "Active swap $swapdev is on $TARGET. Disable it first."
  done < <(swapon --noheadings --raw --show=NAME 2>/dev/null || true)
fi

SIZE="$(lsblk -dnro SIZE "$TARGET" 2>/dev/null || echo '?')"
MODEL="$(cat "/sys/block/$NAME/device/name" 2>/dev/null | tr -d '\r\n' || true)"
CID="$(cat "/sys/block/$NAME/device/cid" 2>/dev/null | tr -d '\r\n' || true)"

cat <<EOF

=== SAFETY CHECK PASSED ===
Target eMMC : $TARGET
Type        : $MMC_TYPE
Size        : $SIZE
Model/name  : ${MODEL:-unknown}
CID         : ${CID:-unknown}
Root source : ${ROOT_SRC:-unknown}
Boot source : ${BOOT_SRC:-unknown}
boot0/boot1 : present

This will:
  1) Force $TARGET and its partitions READ-ONLY in Linux.
  2) Re-apply read-only protection at boot.
  3) Add a udev rule so the guard is applied when the eMMC appears.
  4) Shadow the normal 'armbian-install' command with a blocking wrapper.
  5) Add a login warning.

It will NOT permanently alter the eMMC hardware write-protect bits.
It will NOT make the eMMC unreadable.
A root user can deliberately remove/bypass this software protection.

EOF

read -r -p "Type exactly 'LOCK $NAME' to continue: " CONFIRM
[[ "$CONFIRM" == "LOCK $NAME" ]] || die "Confirmation did not match. Nothing changed."

BLOCKDEV="$(command -v blockdev || true)"
[[ -x "$BLOCKDEV" ]] || die "blockdev command not found."

install -d -m 0755 /usr/local/sbin
install -d -m 0755 /etc/udev/rules.d
install -d -m 0755 /etc/systemd/system
install -d -m 0755 /etc/profile.d
install -d -m 0755 /etc/emmc-guard

cat > /etc/emmc-guard/config <<EOF
EMMC_DEVICE=$TARGET
EMMC_NAME=$NAME
INSTALLED_AT=$(date -Is)
EOF
chmod 0644 /etc/emmc-guard/config

cat > /usr/local/sbin/emmc-guard <<EOF
#!/bin/sh
set -eu
DEV="$TARGET"
BLOCKDEV="$BLOCKDEV"

[ -b "\$DEV" ] || exit 0

"\$BLOCKDEV" --setro "\$DEV"

for node in "\${DEV}"p* "\${DEV}"boot0 "\${DEV}"boot1 "\${DEV}"rpmb; do
    [ -b "\$node" ] || continue
    "\$BLOCKDEV" --setro "\$node" 2>/dev/null || true
done
EOF
chmod 0755 /usr/local/sbin/emmc-guard
chown root:root /usr/local/sbin/emmc-guard

cat > /etc/udev/rules.d/99-emmc-readonly.rules <<EOF
# Protect the internal eMMC from accidental writes.
ACTION=="add", SUBSYSTEM=="block", KERNEL=="$NAME", RUN+="/usr/local/sbin/emmc-guard"
ACTION=="add", SUBSYSTEM=="block", KERNEL=="${NAME}p*", RUN+="/usr/local/sbin/emmc-guard"
EOF
chmod 0644 /etc/udev/rules.d/99-emmc-readonly.rules

cat > /etc/systemd/system/emmc-guard.service <<'EOF'
[Unit]
Description=Force internal eMMC read-only
After=systemd-udevd.service
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/emmc-guard
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 /etc/systemd/system/emmc-guard.service

# Shadow the normal installer without modifying the vendor-provided copy.
cat > /usr/local/sbin/armbian-install <<'EOF'
#!/bin/sh
cat >&2 <<'MSG'
BLOCKED: armbian-install is intentionally disabled on this machine.
The internal eMMC is protected and must not be used for an Armbian installation.
If you are the system owner and truly intend to change this policy, inspect:
  /etc/emmc-guard/
  /usr/local/sbin/emmc-guard
  /etc/udev/rules.d/99-emmc-readonly.rules
  /etc/systemd/system/emmc-guard.service
MSG
exit 126
EOF
chmod 0755 /usr/local/sbin/armbian-install
chown root:root /usr/local/sbin/armbian-install
ln -sfn /usr/local/sbin/armbian-install /usr/local/bin/armbian-install

cat > /etc/profile.d/99-emmc-protected.sh <<EOF
if [ -t 1 ]; then
    printf '%s\n' 'NOTICE: Internal eMMC $TARGET is intentionally protected READ-ONLY. Do not install Armbian to eMMC.'
fi
EOF
chmod 0644 /etc/profile.d/99-emmc-protected.sh

udevadm control --reload-rules 2>/dev/null || true
systemctl daemon-reload
systemctl enable emmc-guard.service >/dev/null
/usr/local/sbin/emmc-guard
systemctl restart emmc-guard.service

RO="$("$BLOCKDEV" --getro "$TARGET" 2>/dev/null || echo '?')"
[[ "$RO" == "1" ]] || die "Guard installed, but $TARGET did not report read-only=1."

hash -r 2>/dev/null || true

echo
echo "=== PROTECTION ENABLED ==="
echo "Read-only state:"
lsblk -o NAME,SIZE,RO,TYPE,MOUNTPOINTS "$TARGET" 2>/dev/null || true
echo
echo "blockdev --getro $TARGET => $RO"
echo
echo "Installer resolution:"
command -v armbian-install || true
echo
echo "Service:"
systemctl --no-pager --full status emmc-guard.service 2>/dev/null | sed -n '1,8p' || true
echo
echo "Protection is active. Reboot once, then verify with:"
echo "  sudo blockdev --getro $TARGET"
echo "  lsblk -o NAME,SIZE,RO,TYPE,MOUNTPOINTS"
echo "  command -v armbian-install"
echo "  sudo armbian-install"
