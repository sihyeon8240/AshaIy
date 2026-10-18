#!/usr/bin/env bash
set -euo pipefail

exec "${PYTHON:-python3}" "${ASHAIY_ROOT:-/workspace}/scripts/ashaiy" "$@"
