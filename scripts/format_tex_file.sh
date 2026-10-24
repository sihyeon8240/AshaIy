#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$repo_root/scripts/run_python.sh" "$repo_root/scripts/format_tex.py" --stdout "$@"
