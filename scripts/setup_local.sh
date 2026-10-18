#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
# shellcheck source=config/toolchain.env
source "$repo_root/config/toolchain.env"

if [[ "$(uname -s)" != Linux ]]; then
  echo "error: local support requires Linux or WSL2" >&2
  exit 1
fi
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 14) else "Python 3.14 or newer is required")'
"$PYTHON" -m venv "$repo_root/.cache/local-venv"
"$repo_root/.cache/local-venv/bin/python" -m pip install \
  --requirement "$repo_root/.github/requirements-ci.txt"
printf 'Local Python environment ready.\nActivate it with: source "%s/.cache/local-venv/bin/activate"\nThen run: ./scripts/ashaiy doctor env\n' "$repo_root"
