#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "usage: $0" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="${PYTHON:-python3}"
: "${GITHUB_SHA:?GITHUB_SHA is required}" "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
cd "$repo_root"
: "${BUILD_PLAN:?BUILD_PLAN is required}"

stop_if_superseded() {
  local remote_sha
  git fetch --no-tags origin main
  remote_sha="$(git rev-parse origin/main)"
  if [[ "$remote_sha" != "$GITHUB_SHA" ]]; then
    echo "A newer main commit exists; its cumulative workflow will publish."
    echo "current=false" >> "$GITHUB_OUTPUT"
    exit 0
  fi
}
stop_if_superseded

if git ls-remote --exit-code --heads origin generated-pdfs > /dev/null; then
  snapshot_exists=true
else
  status=$?
  if [[ "$status" -ne 2 ]]; then
    echo "error: could not determine the remote PDF snapshot state" >&2
    exit "$status"
  fi
  snapshot_exists=false
fi

snapshot="$(mktemp -d "${TMPDIR:-/tmp}/textbook-snapshot.XXXXXXXX")"
bootstrap_branch=""
cleanup() {
  local previous
  for previous in "$snapshot"/.pdf-staging-*/previous; do
    if [[ -d "$previous" ]]; then
      echo "Snapshot recovery worktree retained: $snapshot" >&2
      return
    fi
  done
  if git worktree remove --force "$snapshot"; then
    if [[ -n "$bootstrap_branch" ]]; then
      git update-ref -d "refs/heads/$bootstrap_branch"
    fi
  else
    rmdir "$snapshot" 2> /dev/null || true
  fi
}
trap cleanup EXIT

if [[ "$snapshot_exists" == true ]]; then
  git fetch --no-tags origin generated-pdfs
  git worktree add --detach "$snapshot" origin/generated-pdfs
else
  git worktree add --detach "$snapshot"
  branch="snapshot-bootstrap-${snapshot##*/}"
  git -C "$snapshot" switch --orphan "$branch"
  bootstrap_branch="$branch"
  git -C "$snapshot" rm -r --ignore-unmatch .
fi

"$PYTHON" scripts/release/snapshot_state.py "$snapshot" updated-pdfs --build-plan "$BUILD_PLAN"

printf '%s\n' "$GITHUB_SHA" > "$snapshot/.source-sha"
cp .github/generated-pdfs-README.md "$snapshot/README.md"

git -C "$snapshot" add .source-sha README.md pdf
if git -C "$snapshot" diff --cached --quiet; then
  :
else
  status=$?
  if [[ "$status" -ne 1 ]]; then
    echo "error: could not compare the prepared PDF snapshot" >&2
    exit "$status"
  fi
  git -C "$snapshot" \
    -c 'user.name=github-actions[bot]' \
    -c 'user.email=41898282+github-actions[bot]@users.noreply.github.com' \
    commit -m "Update PDFs from ${GITHUB_SHA}"
fi

stop_if_superseded

# Verify the remote write even when the prepared tree was already unchanged.
git -C "$snapshot" push origin HEAD:generated-pdfs
snapshot_sha="$(git -C "$snapshot" rev-parse HEAD)"
{
  echo "current=true"
  echo "snapshot_sha=$snapshot_sha"
} >> "$GITHUB_OUTPUT"
