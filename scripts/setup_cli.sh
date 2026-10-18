#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Existing pinned images may predate the image-installed launcher.
mkdir -p "$repo_root/.cache/bin"
ln -sfn "$repo_root/scripts/ashaiy_launcher.sh" "$repo_root/.cache/bin/ashaiy"
