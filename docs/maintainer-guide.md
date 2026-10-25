# Maintainer guide

This guide owns review, publication, and recovery. Use
[architecture](ARCHITECTURE.md) for file ownership,
[the developer workflow](developer-workflow.md) for release preparation, and
[book registry and site guide](site-metadata.md) for metadata and local previews.

## Reviewing changes

Check AI-assisted work for invented citations, unsupported claims, and
unnecessary rewrites, alongside the requirements below.

## Pull-request checklist

- The batch is manageable to review; unrelated changes use separate commits,
  large or risky changes use separate PRs, and parts needed for one coherent
  result stay together.
- Generated files follow the [storage and tracking policy](ARCHITECTURE.md#generated-files-and-local-outputs); no build artifacts or local-only assets are added.
- Mathematics, includes, labels, citations, metadata ownership, and rights are correct.
- The checks required by [Contributing](CONTRIBUTING.md#validation-by-change-category) passed; unavailable checks are explained.
- Warnings and intentional limitations are stated.

## Release checklist

- Follow [release preparation](developer-workflow.md#releases) on a development
  branch and review the version, flags, and generated assembly in the PR.
- Review the PR PDF before merging. Merging the release preparation authorizes
  automatic publication after main CI succeeds.
- Confirm the public release contains the versioned PDF and `SHA256SUMS`, and
  that its annotated tag points to the validated main commit.
- Preserve existing tags and assets. Recover failures through the original
  workflow's failed jobs using the
  [recovery procedure](#recovering-an-interrupted-release).

## Release publication

`build.yml` plans releases from the PR base or main push's `before` commit,
independently of the PDF snapshot baseline. Review planned books, versions, and
tags in its summary. Existing tags or failed lookups reject the PR plan;
publication checks again after merge. Release targets always enter the PDF
matrix. PRs validate; manual **Build textbooks** runs refresh development PDFs.

After source, Lean, formatting, and strict PDF gates pass, `release.yml` publishes
same-run `<slug>-release` packages retained for 90 days. They contain the checked
PDF, `SHA256SUMS`, and `release-build.json`, binding bytes to book, version,
source commit, run, and attempt.

Publication creates an annotated `<slug>-v<version>` tag at the validated commit,
uploads the versioned PDF and checksums to a draft, downloads and verifies them,
then publishes. Prerelease suffixes mark prereleases; the title is the book tag,
notes are repository-wide, and no book claims `Latest`. Publication leaves the
manifest's descriptive `status` unchanged. Only publication jobs receive release
write permission; Pages and versioned releases are independent.

### Recovering an interrupted release

- Use **Re-run failed jobs** on the original main **Build textbooks** run, or
  dispatch **Retry original textbook release** (`release-retry.yml`) on main
  with `source_run_id`, `book`, and the original `version` without a `v` prefix.
  Recovery checks the original source, artifact identity, and the gates of the
  attempt recorded in the package, then publishes its retained bytes without
  rebuilding. A new **Build textbooks** dispatch does not recover old releases.
- If publication failed after packaging, retain the original `<slug>-release`
  artifact. Avoid rerunning successful build jobs: a rebuilt PDF can differ in
  bytes, and an existing immutable artifact must not be replaced.
- Re-enabling a previously published book does not reset its release history.
  Choose a higher version if its current version already has a tag.
- An existing tag must be annotated and point to the validated commit. Every
  attempt must successfully push it without force before accessing the release.
  Resolve remote failures before retrying. Existing draft assets must match the
  package byte for byte; only missing assets are uploaded.
- Retries verify public assets against the original package without changing the
  release. Matching assets complete safely after a lost connection; missing or
  different assets fail verification.
- If a retained package has expired or conflicting bytes cannot be recovered,
  leave the draft unpublished and prepare a reviewed higher version. Never move
  an existing tag or overwrite public assets to force recovery.
- Publication and retries queue per book and retain all waiting versions. Later
  main commits do not suppress earlier releases or backfill failed ones.
  Recover cancelled or failed runs explicitly.

## Site publication checklist

For initial setup:

1. In **Settings → Pages → Build and deployment**, choose **GitHub Actions** as
   the source. `configure-pages` checks the existing configuration; this workflow
   does not enable Pages or change repository permissions automatically.
2. If the `github-pages` environment has deployment branch restrictions, ensure
   `main` is allowed. Keep existing required reviews and other protection rules.
   The deployment job itself also accepts only `main`.
3. Merge reviewed changes or dispatch **Build textbooks** on main. This
   builds the initial complete PDF set, creates `generated-pdfs`, and deploys it.
   **Deploy static site** alone requires an existing snapshot and cannot bootstrap
   missing PDFs.
4. Open the deployment URL and check the index, a book detail page, and its PDF
   read/download links. If setup fails, inspect the Pages configuration and
   environment approval state before rerunning the failed job.

To retry deployment without rebuilding PDFs, dispatch **Deploy static site** on
main. It renders the current snapshot's recorded source, not arbitrary newer
source changes. To publish new source or replace missing/expired PDF artifacts,
dispatch **Build textbooks** on main instead. A superseded deployment exits
successfully without uploading or deploying an older snapshot.

Snapshot writes queue without evicting waiting runs. CI checks current main,
requires artifacts to match the build matrix and complete site PDF set, then
prepares replacements and removals before pushing. Missing or expired artifacts
leave `.source-sha` unchanged; dispatch **Build textbooks** for fresh artifacts.
Main is checked again before the push.

For failures:

- Preparation failures leave existing PDFs available. Installation errors and
  Python cancellation exceptions restore the previous directory. If restoration
  fails, the error retains its recovery path: restore `.pdf-staging-*/previous/`
  as that worktree's `pdf/`. Abrupt termination is not transactional; inspect
  retained staging before reuse.
- Each Git attempt uses a temporary worktree, removed on normal completion or
  failure. Restoration failures preserve and report it. Retry from the remote
  snapshot; do not reuse a failed attempt's local commit.
- Only an explicit absent-branch result (`git ls-remote --exit-code` status 2)
  permits bootstrap. Lookup, diff, transport, and push errors fail publication.
  Concurrent snapshot changes reject the fast-forward push; fetch and retry.
  Even unchanged snapshots must push successfully before success is reported.

Changes to the Pages workflow advance the site source snapshot without requiring
PDF rebuilds, so the workflow and its source scripts remain compatible.

Pages uses the immutable `snapshot_sha` and its recorded source. Deployment jobs
queue; guards preserved before loading that source check for supersession before
rendering and immediately before deployment. The artifact checker validates
rendered links and PDF bytes before upload. Remote/ref failures stop deployment:
restore access or repair the ref, then retry. Main and the snapshot ref are not
locked as one transaction. Versioned release packages are independent.

## Drift detection

Use `ashaiy check source` for structural validation, `ashaiy report` for repository
health, and `ashaiy doctor book --book <slug>` for advisory book inspections.
Review shared changes against every affected consumer and preserve public interfaces.

## CI caches and verified PDF reuse

Cache hits still run normal builds and strict checks. Lean caches include
platform, toolchain, lock, configuration, and source inputs; PDF caches include
the book, platform, image digest, and shared build inputs. Fallback stays within
the same book and image. Only successful main pushes save Lean and PDF caches;
PRs restore them. Python and Mathlib download directories are not separately
restored by Actions.

Formatter caches use implementation and configuration inputs. CI prunes obsolete
generations with `python3 scripts/latex/format_tex.py --check --prune-cache` before
saving. Use pruning locally only without concurrent formatter runs.
[Cache cleanup](developer-workflow.md#cleaning-outputs-and-caches) lists local paths.

PDF reuse, image candidates, and release retries share bounded, file-based
downloads in [`github_artifacts.py`](../scripts/ci/github_artifacts.py): progress,
disk-space, size, timeout/retry, provenance, and GitHub digest checks. Domain
modules validate their own archive contents.

After a merge, each affected PDF job first looks for a successful `build.yml`
PR run, or an exact-pin dispatch, for the merged PR's head in this repository.
A dispatch must match the PR branch and record `expected_sha`; unpinned dispatches
do not produce reusable validation artifacts. Reuse requires an identical
full Git tree (including workflows and build settings), image index digest,
platform, validation policy, run ID/attempt, and PDF/log checksums. The downloaded
archive must also match GitHub's artifact digest, and its log is strictly checked
again. GitHub commit trees are compared before artifact lookup and download.
A match skips the TeX container build and republishes the verified PDF as
the current run's artifact for snapshot publication.

Verified artifacts expire after 14 days; unavailable or ineligible artifacts
fall back to a normal cached build. Full-tree matching is conservative: an
unrelated change can require a rebuild, while merge/squash/rebase commit SHAs may
differ if their final trees match. Manual **Build textbooks** dispatches skip
PR reuse and build every enabled book. Bump cache versions or `strict-pdf-v1`
when their corresponding semantics change.

## Toolchain image operations

### Multi-platform toolchain images

Manual **Validate and publish toolchain image** runs validate existing images by
default (`validate_existing`). Disable this only for publication/cache maintenance.
Ordinary source changes do not add another platform matrix. Verified PDF reuse
remains AMD64-only; ARM64 checks produce no reusable publication artifacts.

Image builds restore `buildcache-<arch>` registry caches, falling back to the
latest image's inline cache. Non-PR builds export intermediate stages; PRs only
read them. Cache refresh preserves the tested image and independent TeX Live stage.

The package is `ghcr.io/sihyeon8240/ashaiy`. `build.yml` calls
`prepare-image.yml`, which derives a content tag and calls `build-toolchain.yml`.
Main waits for publication before using the immutable index. The manual
`build-image.yml` recovery workflow does not also run on pushes. Ordinary PRs resolve
the published tag for their inputs; `config/container-image.txt` remains the local
and Dev Container pin. Registry errors fail explicitly.
Resolution fixes one verified index digest for platform validation and consumers;
each builder pulls that digest instead of resolving the tag again.

Reusing a published image does not refresh intermediate caches. Use the manual
workflow's `refresh_cache` input when needed.

#### Validating an image PR

1. Both native runners must be available: `ubuntu-26.04` for AMD64 and
   `ubuntu-26.04-arm` for ARM64. Both platforms strictly build every checked
   textbook. ARM64 additionally runs the real Lean-code/font rendering fixtures
   and the Chromium site suite; the ordinary AMD64 consumers run those same
   rendering checks. Each candidate passes architecture and toolchain
   smoke checks.
   Image-pipeline PRs rerun these checks on an existing published image as well,
   without rebuilding it or exporting redundant candidate archives.
2. Formatting and PDF jobs consume the tested AMD64 candidate. Before registry
   publication they verify a run-local archive's image ID and architecture.
   Candidate failure blocks **Check sources** and downstream consumers.
3. Candidate PDF/log archives may skip repeated builds only within the same run
   and attempt, with matching source tree, image ID, policy, and checksums plus
   a fresh strict log check. Missing or invalid PDFs fall back to normal builds.
   These archives do not qualify for registry-digest reuse after merge.
4. Wait for the pin commit and its final consumer CI before merging. Candidate
   archives expire after 14 days; rerun PR CI if they expire or the merge tree moves.

#### Publication and pinning

PR jobs are read-only: same-repository jobs may authenticate for package reads;
forks use anonymous pulls. After successful same-repository PR CI,
`pin-pr-image.yml` runs trusted main code to promote candidates. It accepts only
open PRs targeting main whose current head matches the successful run, including
Dependabot PRs. Bring fork image changes into a same-repository PR for promotion.

Promotion verifies both architecture artifacts, GitHub digests, policy, source
tree, content tag, run/attempt, archive checksums, image IDs, and architectures. It never
executes PR scripts or candidate containers with write credentials. Changed or
closed heads are skipped; mismatched merge trees require fresh CI.

Downloads, extraction, loading, and publication report progress and enforce size,
disk-space, and time limits. Consult [artifact transport](#ci-caches-and-verified-pdf-reuse)
and the failed stage's log before retrying. Publication code comes from `main`;
changes take effect only after owner review and merge.

After publishing the index, the publisher adds one commit changing only
`config/container-image.txt` and `.devcontainer/devcontainer.json` to the original
PR branch. An isolated index and exact-head push lease protect concurrent author
changes. Retries skip applied pins. The destination comes from trusted main
configuration; no separate pin PR or branch is created.

After pushing a pin with `GITHUB_TOKEN`, the publisher dispatches **Build
textbooks** on the PR branch with the exact expected commit. Dispatch events run
automatically without a GitHub App, PAT, or approval of the separate PR-event run.
Transient dispatch failures retry the same committed pin up to three times.
The source gate rejects a dispatch if the branch moved before it started. Final
consumer CI resolves the published image and does not trigger another publisher.
If dispatch fails, manually dispatch **Build textbooks** on the PR branch with
`expected_sha` set to the pin commit; do not rerun CI on the pre-pin commit.
Ordinary textbook PRs neither publish images nor update pins.

The content tag hashes inputs and build policy from `config/image-build.json`.
The published transcript contains each input's SHA-256 and path, followed by the
policy version and ordered platforms. This format is a wire contract shared by
the independently deployed PR validator and trusted main publisher. Keep it stable
when either side is updated first; a policy-version bump alone cannot teach an
older publisher a different serialization algorithm.

Docker `COPY --chmod` fixes executable and data permissions in the recipe. Checkout
mode bits therefore do not affect the image; permission-policy changes modify the
Dockerfile bytes and its content tag. The hash command rejects symlinks, unhashed
repository COPY sources, and repository COPY instructions without explicit modes.
Base images and external COPY sources require immutable digests; local build
inputs use literal COPY paths rather than ADD.
This identifies declared build inputs and a tested publication. It does not promise
identical bytes from independent rebuilds: apt resolution and Python transitive
dependencies are not fully locked. Consumers use the published immutable digest.
Review the policy version when hash, build, or validation semantics change.
Existing indexes must contain both Linux platforms and are never overwritten.
Only an explicit missing manifest permits a build; denied lookups fail.
Publication rechecks the registry under a serialized content-tag lock. Preparation
uses `cancel-in-progress: false` and `queue: max` to retain waiting runs.
Temporary per-architecture tags may remain after partial failure; the final index
is published only after both smoke tests pass. Main may reuse matching successful
PR artifacts or fall back to building from source.

#### Recovery and registry access

Main bootstraps its image automatically, even for a private package. Publication
reports the digest, platforms, local-pin drift, and anonymous index access in the
job summary. Only the current main commit advances `latest` and its source-SHA
alias, including when reusing a previously published PR image. A new publication
does not directly change the local pin on main. Main and
same-repository PRs need package-read access; existing GHCR packages must grant
this repository Actions access. Public repository visibility does not make its
package public. Fork PRs and anonymous local pulls require a public package.

For missing images or a repository move:

1. Dispatch **Validate and publish toolchain image** (`build-image.yml`) on main.
   The publisher needs package-write access; denied registry lookups remain errors.
2. Make the GHCR package public if anonymous pulls are needed.
3. Inspect the published index with
   `docker buildx imagetools inspect ghcr.io/sihyeon8240/ashaiy:latest`.
   Verify anonymous access when required, then run
   `ashaiy image pin --digest <sha256>` on a development branch and submit the
   synchronized pin in a PR. Do not copy an unverified digest from another registry.
4. Run consumer CI. Its image resolution does not depend on updating the local pin.

For an open PR, rerun its CI to retry promotion. If it merged before pinning,
prepare the recovered pin in a later development PR. `build-image.yml` publishes
only on main and does not update main directly or create follow-up PRs.

Keep default workflow token permissions read-only; workflows declare their own
writes. There are no automatic approval or merge steps. Use GitHub's
**Automatically delete head branches** setting for merged PRs.
Changed-path and source/PDF baseline ownership is documented in
[architecture](ARCHITECTURE.md#repository-automation-modules); source selection
can omit Lean setup for non-Lean changes while keeping other checks enabled.

### Toolchain updates

Review manually managed Python packages and toolchain versions monthly, and
promptly when a security advisory or end-of-support notice applies. Dependabot
tracks Actions and Docker only.

Keep the Python version and base-image digest pinned. Dependabot ignores the
`python` Docker image; update it manually only when needed for a security fix,
end of support, or a dependency requirement. Update `config/toolchain.env` and
the Python image pin in `.devcontainer/Dockerfile` together, then run
`ashaiy config generate`, `ashaiy config check`, `ashaiy test`, and `ashaiy check all --strict`
using the rebuilt development image.

The image includes local site/browser and PDF inspection tools. Their system
packages follow the Debian Trixie base in `.devcontainer/Dockerfile`; Jekyll and
Bundler upstream versions are checked against `config/toolchain.env`, and
Playwright uses installed Chromium. The reviewed image digest pins the installed
set; rebuilding can pick up newer Debian package revisions.

For package updates, change `config/toolchain.env` first and regenerate
`.github/requirements-ci.txt` with `ashaiy config generate`; update tool binary checksums
for both architectures when their versions change. Validate dependency updates
with the complete suites required by the contributing guide.
