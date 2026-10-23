#!/usr/bin/env bash
set -euo pipefail

# Validate queue settings until the pinned actionlint understands this key.
python3 - <<'PYTHON'
from pathlib import Path

from scripts.source_reads import read_yaml

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

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$root_dir/config/toolchain.env"

version="$ACTIONLINT_VERSION"
archive="actionlint_${version}_linux_amd64.tar.gz"
checksum="$ACTIONLINT_SHA256_AMD64"
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
