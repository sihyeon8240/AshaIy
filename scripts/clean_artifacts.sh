#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "$repo_root" in
/ | "")
  echo "error: refusing unsafe repository root" >&2
  exit 1
  ;;
esac

mapfile -t cleanup_files <"$repo_root/config/generated/cleanup-files.txt"
mapfile -t cleanup_prune <"$repo_root/config/generated/cleanup-prune.txt"

find_arguments=()
for directory in "${cleanup_prune[@]}"; do
  find_arguments+=(-path "$repo_root/$directory" -prune -o)
done

find_arguments+=(-type f '(')
for pattern in "${cleanup_files[@]}"; do
  find_arguments+=(-name "$pattern" -o)
done
find_arguments+=(-false ')' -exec rm -f -- '{}' +)
find "$repo_root" "${find_arguments[@]}"
