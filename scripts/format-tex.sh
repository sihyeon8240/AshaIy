#!/usr/bin/env bash
set -euo pipefail

mode="format"
selected_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
  --check)
    mode="check"
    shift
    ;;
  --file)
    if [[ $# -lt 2 || -n "$selected_file" || -z "$2" ]]; then
      echo "usage: $0 [--check] [--file FILE]" >&2
      exit 2
    fi
    selected_file="$2"
    shift 2
    ;;
  *)
    echo "usage: $0 [--check] [--file FILE]" >&2
    exit 2
    ;;
  esac
done

repository_root="$(git rev-parse --show-toplevel)"
if [[ -n "$selected_file" ]]; then
  selected_file="$(realpath -- "$selected_file")"
  case "$selected_file" in
  "$repository_root"/*.tex | "$repository_root"/*.sty) ;;
  *)
    echo "error: FILE must be an existing .tex or .sty file inside the repository" >&2
    exit 2
    ;;
  esac
  if [[ ! -f "$selected_file" ]]; then
    echo "error: FILE does not exist: $selected_file" >&2
    exit 2
  fi
  if git check-ignore --quiet -- "$selected_file"; then
    echo "error: FILE must not be ignored by Git" >&2
    exit 2
  fi
fi

if ! command -v latexindent >/dev/null 2>&1; then
  echo "error: latexindent is required" >&2
  exit 127
fi

cd "$repository_root"
eof_formatter="$repository_root/scripts/normalize-eof.sh"
format_settings="$repository_root/config/latexindent.yaml"
file_formatter="$repository_root/scripts/format-tex-file.sh"

cruft_directory="$(mktemp -d)"
trap 'rm -rf "$cruft_directory"' EXIT

# Reuse checks only while the source, formatting rules, and tool version match.
cache_root="${FORMAT_TEX_CACHE_DIR:-$repository_root/.cache/latexindent}"
script_hash="$(sha256sum "$0" "$file_formatter" "$eof_formatter" "$format_settings")"
latexindent_version="$(latexindent --version | head -n 1)"
cache_namespace="$(
  printf '%s\n%s\n' "$script_hash" "$latexindent_version" |
    sha256sum | cut -d ' ' -f 1
)"
cache_directory="$cache_root/$cache_namespace"
mkdir -p "$cache_directory"

status=0
file_count=0
cached_count=0
changed_count=0
if [[ "$mode" == "format" ]]; then
  echo "[tex] formatting LaTeX source files"
else
  echo "[tex] checking LaTeX source files"
fi

source_files() {
  if [[ -n "$selected_file" ]]; then
    printf '%s\0' "$selected_file"
  else
    git ls-files -z --cached -- '*.tex' '*.sty'
  fi
}

while IFS= read -r -d '' file; do
  [[ -f "$file" ]] || continue
  file_count=$((file_count + 1))
  path_hash="$(printf '%s' "$file" | sha256sum | cut -d ' ' -f 1)"
  cache_entry="$cache_directory/$path_hash"
  content_hash="$(sha256sum "$file" | cut -d ' ' -f 1)"
  if [[ -f "$cache_entry" ]] && [[ "$(<"$cache_entry")" == "$content_hash" ]]; then
    cached_count=$((cached_count + 1))
    continue
  fi

  "$file_formatter" "$file" >"$cruft_directory/lean-normalized.tex"

  if ! cmp -s "$file" "$cruft_directory/lean-normalized.tex"; then
    if [[ "$mode" == "check" ]]; then
      echo "[tex] needs formatting: $file" >&2
      status=1
      continue
    fi
    cat "$cruft_directory/lean-normalized.tex" >"$file"
    changed_count=$((changed_count + 1))
    echo "[tex] reformatted: $file"
  fi

  sha256sum "$file" | cut -d ' ' -f 1 >"$cache_entry"
done < <(source_files)

if [[ "$status" -ne 0 ]]; then
  exit "$status"
fi

if [[ "$mode" == "format" ]]; then
  unchanged_count=$((file_count - cached_count - changed_count))
  printf '[tex] %s files total: %s cached, %s reformatted, %s unchanged\n' \
    "$file_count" "$cached_count" "$changed_count" "$unchanged_count"
else
  echo "[tex] $file_count files checked, all correctly formatted ($cached_count cached)"
fi
