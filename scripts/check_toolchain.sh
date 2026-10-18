#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/config/toolchain.env"

PYTHON="${PYTHON:-python3}"

pass() {
  printf "  \033[32m✓\033[0m %s\n" "$1"
}

fail() {
  printf "  \033[31m✗\033[0m %s\n" "$1" >&2
  exit 1
}

check_command() {
  local cmd="$1"

  if command -v "$cmd" >/dev/null 2>&1; then
    pass "$cmd found"
  else
    fail "$cmd not found"
  fi
}

check_tex_file() {
  local file="$1"

  if kpsewhich "$file" >/dev/null 2>&1; then
    pass "$file found"
  else
    fail "$file not found"
  fi
}

check_version() {
  local command="$1"
  local expected="$2"
  local label="$3"
  local actual
  local output
  local rc

  if output="$("$command" --version 2>&1)"; then
    actual="$output"
  else
    rc=$?
    fail "$label version command failed (exit $rc): ${output:-no output}"
  fi
  if [[ "$actual" == *"$expected"* ]]; then
    pass "$label found"
  else
    fail "$label not found: $actual"
  fi
}

echo "[Toolchain]"

check_command latexmk
check_command lualatex
check_command latexindent
check_command biber
check_command "$PYTHON"
check_command kpsewhich
check_command rg
check_command gs
check_command tree
check_command git
check_command bash
check_command shellcheck
check_command shfmt
check_command ruff
check_command basedpyright
check_command yamllint
check_command djlint
check_command check-jsonschema
check_command elan
check_command lean
check_command lake
check_command leanc
check_command gh
check_command ruby
check_command bundle
check_command jekyll
check_command chromium
check_command pdfinfo
check_command pdftotext
check_command pdftoppm
check_command jq

check_version "$PYTHON" "Python ${PYTHON_VERSION}" "Python ${PYTHON_VERSION}"
check_version latexindent \
  "${LATEXINDENT_VERSION}, ${LATEXINDENT_RELEASE_DATE}" \
  "latexindent ${LATEXINDENT_VERSION}, ${LATEXINDENT_RELEASE_DATE}"
check_version ruff "ruff ${RUFF_VERSION}" "ruff ${RUFF_VERSION}"
check_version shfmt "v${SHFMT_VERSION}" "shfmt ${SHFMT_VERSION}"
check_version shellcheck "version: ${SHELLCHECK_VERSION}" "ShellCheck ${SHELLCHECK_VERSION}"
check_version elan "elan ${ELAN_VERSION}" "elan ${ELAN_VERSION}"
check_version lean "Lean (version ${LEAN_VERSION}" "Lean ${LEAN_VERSION}"
check_version gh "gh version ${GH_VERSION}" "GitHub CLI ${GH_VERSION}"

check_version jekyll "jekyll ${JEKYLL_VERSION}" "Jekyll ${JEKYLL_VERSION}"
check_version bundle "Bundler version ${BUNDLER_VERSION}" "Bundler ${BUNDLER_VERSION}"

for package in playwright hypothesis coverage basedpyright yamllint djlint check-jsonschema; do
  normalized_package="${package//-/_}"
  version_key="${normalized_package^^}_VERSION"
  installed_version="$("$PYTHON" -c 'import importlib.metadata, sys; print(importlib.metadata.version(sys.argv[1]))' "$package")"
  if [[ "$installed_version" == "${!version_key}" ]]; then
    pass "$package ${!version_key} found"
  else
    fail "$package ${!version_key} not found: $installed_version"
  fi
done

pyyaml_version="$("$PYTHON" -c 'import yaml; print(yaml.__version__)')"
if [[ "$pyyaml_version" == "$PYYAML_VERSION" ]]; then
  pass "PyYAML ${PYYAML_VERSION} found"
else
  fail "PyYAML ${PYYAML_VERSION} not found: $pyyaml_version"
fi

tex_dependencies=(
  fontspec.sty microtype.sty graphicx.sty xcolor.sty enumitem.sty
  hyperref.sty cleveref.sty amsmath.sty amssymb.sty amsthm.sty
  mathtools.sty mathrsfs.sty bm.sty romannum.sty
  biblatex.sty
)
for dependency in "${tex_dependencies[@]}"; do
  check_tex_file "$dependency"
done

echo
echo "Toolchain dependencies are ready."
