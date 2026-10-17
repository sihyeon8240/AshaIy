#!/usr/bin/env bash

set -Eeuo pipefail

# AshaIy - Development Environment Check.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

profile="${1:-full}"
if [[ $# -gt 1 ]]; then
  echo "usage: $0 [pdf|lean|format|site|full]" >&2
  exit 2
fi

cd "${ROOT_DIR}"

echo
echo "=============================================="
echo " Development Environment Check"
echo "=============================================="
echo

pass() {
  printf "  \033[32m✓\033[0m %s\n" "$1"
}

fail() {
  printf "  \033[31m✗\033[0m %s\n" "$1" >&2
  exit 1
}

if [[ "$profile" == full ]]; then
  "${ROOT_DIR}/scripts/check-toolchain.sh"
else
  exec "$PYTHON" "${ROOT_DIR}/scripts/check-local-environment.py" "$profile"
fi

echo

# Repository structure.

echo "[Repository]"

[[ -f scripts/ashaiy ]] &&
  pass "scripts/ashaiy found" ||
  fail "scripts/ashaiy missing"

[[ -f config/latexmkrc ]] &&
  pass "config/latexmkrc found" ||
  fail "config/latexmkrc missing"

[[ -d books ]] &&
  pass "books/ found" ||
  fail "books/ missing"

[[ -d common ]] &&
  pass "common/ found" ||
  fail "common/ missing"

[[ -f common/styles/textbook.sty ]] &&
  pass "textbook.sty found" ||
  fail "common/styles/textbook.sty missing"

echo

mkdir -p build

pass "build/ is ready"

echo

# Versions.

echo "[Versions]"

printf "  LuaLaTeX    : %s\n" \
  "$(lualatex --version | head -n1)"

printf "  latexmk     : %s\n" \
  "$(latexmk -v | head -n1)"

printf "  Biber       : %s\n" \
  "$(biber --version | head -n1)"

printf "  Lean        : %s\n" \
  "$(cd "${ROOT_DIR}/lean" && lean --version | head -n1)"

printf "  Lake        : %s\n" \
  "$(cd "${ROOT_DIR}/lean" && lake --version | head -n1)"

printf "  Mathlib     : %s\n" \
  "$("$PYTHON" -c '
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    packages = json.load(stream)["packages"]
mathlib = next(package for package in packages if package["name"] == "mathlib")
print("{} ({})".format(mathlib["inputRev"], mathlib["rev"][:12]))
' "${ROOT_DIR}/lean/lake-manifest.json")"

printf "  Elan        : %s\n" \
  "$(elan --version)"

printf "  Python      : %s\n" \
  "$("$PYTHON" --version)"

printf "  PyYAML      : %s\n" \
  "$("$PYTHON" -c 'import yaml; print(yaml.__version__)')"

printf "  CLI         : %s\n" \
  "$("${ROOT_DIR}/scripts/ashaiy" --version)"

printf "  Git         : %s\n" \
  "$(git --version)"

printf "  ripgrep     : %s\n" \
  "$(rg --version | head -n1)"

printf "  Ghostscript : %s\n" \
  "$(gs --version)"

echo
echo "Environment is ready."
