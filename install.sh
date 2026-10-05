#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Beginner entry point. Validated Python installer owns all boot-file writes.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install_mode=--apply
case "${1:-}" in
  '') ;;
  --dry-run) install_mode=--dry-run ;;
  *) echo 'Cách chạy: sudo bash install.sh [--dry-run]' >&2; exit 2 ;;
esac
if (( $# > 1 )); then
  echo 'Cách chạy: sudo bash install.sh [--dry-run]' >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Thiếu Python 3. Cài bằng: sudo apt-get update && sudo apt-get install python3' >&2
  exit 1
fi
if [[ "$install_mode" == --apply && "$EUID" != 0 ]]; then
  echo 'Hãy chạy: sudo bash install.sh' >&2
  exit 1
fi
printf '\nMagicsee N5 Max S905X3 — cài DTB Ethernet\n'
echo 'Đang kiểm tra kernel, checksum, rescue và cấu hình boot...'
# set -e stops on failure: never print a reboot instruction after an error.
python3 "$project_dir/scripts/install.py" "$install_mode"
if [[ "$install_mode" == --dry-run ]]; then
  printf '\nKIỂM TRA THÀNH CÔNG. Chưa ghi file.\n'
  echo 'Để cài: sudo bash install.sh'
else
  printf '\nHOÀN TẤT. DTB release đã được chọn; DTB rescue vẫn giữ nguyên.\n'
  echo 'Cắm dây LAN rồi tự khởi động lại bằng lệnh:'
  echo '  sudo reboot'
  echo 'Sau reboot: sudo ethtool eth0'
fi
