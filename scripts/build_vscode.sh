#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <output-directory> <document> [latexmk-options...]" >&2
  exit 2
fi

out_dir="$1"
document="$2"
shift 2

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
document_dir="$(cd "$(dirname "$document")" && pwd)"
document_name="$(basename "$document")"

if [[ ! -f "$document_dir/$document_name" ]]; then
  echo "error: LaTeX document not found: $document" >&2
  exit 2
fi

# shellcheck source=scripts/build_support.sh
source "$repo_root/scripts/build_support.sh"
build_document "$repo_root" "$document_dir" "$out_dir" "$document_name" "$@"
