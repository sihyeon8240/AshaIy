#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo_root"
PYTHON="${PYTHON:-python3}"

if [[ $# -gt 1 || ($# -eq 1 && "$1" != --defer-proof-links && "$1" != --defer-lean) ]]; then
  echo "usage: $0 [--defer-proof-links|--defer-lean]" >&2
  exit 2
fi

if ! command -v rg > /dev/null 2>&1; then
  echo "error: required command 'rg' (ripgrep) was not found in PATH" >&2
  exit 127
fi
if ! command -v shellcheck > /dev/null 2>&1; then
  echo "error: required command 'shellcheck' was not found in PATH" >&2
  exit 127
fi

mapfile -d '' scripts < <(find scripts -type f -name '*.sh' -print0)
for script in "${scripts[@]}"; do
  bash -n "$script"
done
shellcheck --severity=error "${scripts[@]}"

"$PYTHON" scripts/repository/checks/check_quality.py
"$PYTHON" scripts/repository/checks/source_checks.py "$@"

echo "Repository source checks passed."
