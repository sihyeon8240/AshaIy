#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -eq 0 ]]; then
  set -- full
fi
exec "${PYTHON:-python3}" "$repo_root/scripts/check_local_environment.py" "$@"
