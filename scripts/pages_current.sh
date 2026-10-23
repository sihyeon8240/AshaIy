#!/usr/bin/env bash
set -euo pipefail

: "${SNAPSHOT_SHA:?SNAPSHOT_SHA is required}" "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
# validation-pattern: git_commit
[[ "$SNAPSHOT_SHA" =~ ^[0-9a-f]{40}$ ]]
git fetch --no-tags origin generated-pdfs
remote_sha="$(git rev-parse --verify 'origin/generated-pdfs^{commit}')"
current=false
if [[ "$remote_sha" == "$SNAPSHOT_SHA" ]]; then
  current=true
else
  echo "A newer snapshot exists; skipping this superseded deployment."
fi
echo "current=$current" >>"$GITHUB_OUTPUT"
