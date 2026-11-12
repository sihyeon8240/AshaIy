#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "usage: IMAGE=<tag> $0" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
image="${IMAGE:-ashaiy-toolchain:local}"
target="${IMAGE_TARGET:-dev}"
if [[ "$target" != dev && "$target" != pdf ]]; then
  echo "error: IMAGE_TARGET must be dev or pdf" >&2
  exit 2
fi

exec docker build --target "$target" --tag "$image" --file "$repo_root/.devcontainer/Dockerfile" "$repo_root"
