#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python3 "$repo_dir/scripts/verify.py" --compile --output "$repo_dir/build/meson-sm1-magicsee-n5-max.dtb"
