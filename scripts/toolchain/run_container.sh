#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "usage: IMAGE=<ref> CMD=<command> $0" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "${PYTHON:-python3}" "$repo_root/scripts/toolchain/devcontainer_runner.py"
