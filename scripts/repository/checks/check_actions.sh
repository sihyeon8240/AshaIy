#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PYTHON="${PYTHON:-python3}"
cd "$root_dir"

# Validate queue settings until the pinned actionlint understands this key.
"$PYTHON" - << 'PYTHON'
from pathlib import Path

from scripts.repository.source_reads import read_yaml

for path in sorted(Path(".github/workflows").glob("*.yml")):
    workflow = read_yaml(path)
    for scope in (workflow, *workflow.get("jobs", {}).values()):
        concurrency = scope.get("concurrency")
        if not isinstance(concurrency, dict) or "queue" not in concurrency:
            continue
        if (
            concurrency["queue"] != "max"
            or concurrency.get("cancel-in-progress", False) is not False
        ):
            raise SystemExit(
                f"{path}: queue must be max with cancel-in-progress disabled"
            )
PYTHON

# shellcheck disable=SC1091
source "$root_dir/config/toolchain.env"

version="$ACTIONLINT_VERSION"
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64)
    architecture=amd64
    checksum="$ACTIONLINT_SHA256_AMD64"
    ;;
  Linux/aarch64 | Linux/arm64)
    architecture=arm64
    checksum="$ACTIONLINT_SHA256_ARM64"
    ;;
  *)
    echo "error: actionlint validation requires Linux AMD64 or ARM64" >&2
    exit 2
    ;;
esac
archive="actionlint_${version}_linux_${architecture}.tar.gz"
url="https://github.com/rhysd/actionlint/releases/download/v${version}/${archive}"
temporary="$(mktemp -d)"
trap 'rm -rf -- "$temporary"' EXIT

curl --fail --location --silent --show-error \
  --output "$temporary/$archive" "$url"
printf '%s  %s\n' "$checksum" "$temporary/$archive" | sha256sum --check
tar -xzf "$temporary/$archive" -C "$temporary" actionlint
# actionlint 1.7.12 predates concurrency.queue; keep the exception exact.
"$temporary/actionlint" -color \
  -ignore '^unexpected key "queue" for "concurrency" section\. expected one of "cancel-in-progress", "group"$'
