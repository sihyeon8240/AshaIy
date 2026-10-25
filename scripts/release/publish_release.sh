#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <book-slug> <package-directory>" >&2
  exit 2
fi

source_sha="${RELEASE_SOURCE_SHA:-${GITHUB_SHA:?GITHUB_SHA is required}}"

valid_event=false
if [[ "${GITHUB_EVENT_NAME:-}" == push ]]; then
  valid_event=true
elif [[ "${GITHUB_EVENT_NAME:-}" == workflow_dispatch &&
  "${RELEASE_RETRY_VALIDATED:-}" == "$source_sha" ]]; then
  valid_event=true
fi

if [[ "${GITHUB_ACTIONS:-}" != true || "${GITHUB_REF:-}" != refs/heads/main ||
  "$valid_event" != true ]]; then
  echo "error: publication requires a main push workflow or a validated original-package retry" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
slug="$1"
package="$(cd "$2" && pwd)"
version="$(python3 scripts/books/books.py version "$slug")"
tag="$slug-v$version"

./scripts/release/release_plan.sh "$tag" > /dev/null
[[ "$(git rev-parse HEAD)" == "$source_sha" ]] || {
  echo "error: checkout does not match the validated commit" >&2
  exit 1
}

git fetch --no-tags origin main
git merge-base --is-ancestor "$source_sha" origin/main

(
  cd "$package"
  test -s "$tag.pdf"
  test "$(wc -l < SHA256SUMS)" -eq 1
  [[ "$(cat SHA256SUMS)" == "$(sha256sum "$tag.pdf")" ]]
)

# Fetch tags without force: an existing tag must never move.
git fetch origin 'refs/tags/*:refs/tags/*'
if git rev-parse --verify --quiet "refs/tags/$tag" > /dev/null; then
  [[ "$(git rev-list -n 1 "$tag")" == "$source_sha" &&
  "$(git cat-file -t "refs/tags/$tag")" == tag ]] || {
    echo "error: existing release tag has a conflicting commit or is not annotated" >&2
    exit 1
  }
else
  git config user.name 'github-actions[bot]'
  git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
  git tag -a "$tag" "$source_sha" -m "Release $slug version $version"
fi
git push origin "refs/tags/$tag"

# Listing must succeed; authorization/network failures are not missing releases.
draft="$(gh api "repos/$GITHUB_REPOSITORY/releases" --paginate \
  --jq ".[] | select(.tag_name == \"$tag\") | .draft")"

if [[ -z "$draft" ]]; then
  options=(--draft --verify-tag --generate-notes --latest=false --title "$tag")
  [[ "$version" != *-* ]] || options+=(--prerelease)
  gh release create "$tag" "${options[@]}"
fi

if [[ "$draft" != false ]]; then
  ./scripts/release/upload_release_assets.sh "$tag" "$package/$tag.pdf" "$package/SHA256SUMS"
fi

# Verify bytes downloaded from GitHub before making the release public.
verification="$(mktemp -d)"
trap 'rm -rf -- "$verification"' EXIT
gh release download "$tag" \
  --pattern "$tag.pdf" \
  --pattern SHA256SUMS \
  --dir "$verification"
cmp "$package/$tag.pdf" "$verification/$tag.pdf"
cmp "$package/SHA256SUMS" "$verification/SHA256SUMS"

if [[ "$draft" == false ]]; then
  echo "==> $tag is already public; verified its assets without changes"
  exit 0
fi

gh release edit "$tag" --draft=false --latest=false
echo "==> Published $tag"
