#!/usr/bin/env bash
set -euo pipefail

output_file="${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
image_ref="${IMAGE_REF:-${IMAGE_NAME:?IMAGE_NAME is required}:${RELEASE_TAG:?RELEASE_TAG is required}}"

error_log="$(mktemp)"
trap 'rm -f -- "$error_log"' EXIT

for attempt in 1 2 3; do
  if manifest="$(timeout 60s docker manifest inspect "$image_ref" 2>"$error_log")"; then
    break
  fi

  # Only a missing manifest authorizes building an immutable tag.
  if grep -Eq '^(no such manifest:|manifest unknown([: ]|$))' "$error_log"; then
    if [[ "${REQUIRE_IMAGE:-false}" == true ]]; then
      echo "error: required image is unavailable: $image_ref" >&2
      exit 1
    fi
    echo "No published image for $image_ref; a source build is required." >&2
    echo "exists=false" >>"$output_file"
    exit 0
  fi

  cat "$error_log" >&2
  if ((attempt == 3)); then
    echo "error: cannot determine whether image exists: $image_ref" >&2
    if grep -Eqi 'denied|unauthorized|authentication required' "$error_log"; then
      echo "Check GHCR login and package access for publishers; consumers require a public image." >&2
      echo "See docs/maintainer-guide.md#multi-platform-toolchain-images for initial publication and pin recovery." >&2
    fi
    exit 1
  fi
  sleep "$attempt"
done

if [[ "$image_ref" == *@sha256:* ]]; then
  digest="${image_ref##*@}"
  image="$image_ref"
else
  digest="$(timeout 60s docker buildx imagetools inspect "$image_ref" --format '{{.Manifest.Digest}}')"
  repository="$image_ref"
  if [[ "${repository##*/}" == *:* ]]; then
    repository="${repository%:*}"
  fi
  image="${repository}@${digest}"
fi
# validation-pattern: image_digest
if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "error: registry returned an invalid index digest: $image_ref" >&2
  exit 1
fi
if [[ "$image" != "$image_ref" ]]; then
  manifest="$(timeout 60s docker manifest inspect "$image")"
fi

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! printf '%s' "$manifest" | python3 -c '
import json
import sys

sys.path.insert(0, sys.argv[1])
from scripts.repository_config import load_image_build

required = {("linux", platform["arch"]) for platform in load_image_build()["platforms"]}
manifest = json.load(sys.stdin)
platforms = {
    (entry.get("platform", {}).get("os"), entry.get("platform", {}).get("architecture"))
    for entry in manifest.get("manifests", [])
}
sys.exit(not required <= platforms)
' "$root_dir"; then
  echo "error: existing image lacks the configured platform index: $image_ref" >&2
  echo "Bump the image build policy version; immutable tags must not be overwritten." >&2
  exit 1
fi

echo "Reusing published multi-platform image: $image" >&2
{
  echo "exists=true"
  echo "image=$image"
  echo "digest=${digest#sha256:}"
} >>"$output_file"
