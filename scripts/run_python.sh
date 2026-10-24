#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="${PYTHON:-}"
if [[ -z "$python" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  python="$VIRTUAL_ENV/bin/python"
fi
if [[ -z "$python" && -x "$repo_root/.cache/local-venv/bin/python" ]]; then
  python="$repo_root/.cache/local-venv/bin/python"
fi
exec "${python:-python3}" "$@"
