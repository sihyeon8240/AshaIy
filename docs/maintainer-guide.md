# Maintainer guide

Use [the architecture guide](ARCHITECTURE.md) for repository structure and
ownership, and the [documentation map](README.md) to find task-specific policies.

## Reviewing changes

Review scope, mathematical correctness, provenance, labels, citations, metadata,
generated files, and validation. Check AI-assisted work for invented citations,
unsupported claims, and unnecessary rewrites. Use the
[architecture contract](ARCHITECTURE.md) for ownership and the
[validation matrix](CONTRIBUTING.md#validation-by-change-category) for required gates.

## Pull-request checklist

- The batch is manageable to review; unrelated changes use separate commits,
  large or risky changes use separate PRs, and parts needed for one coherent
  result stay together.
- Generated files follow the [storage and tracking policy](ARCHITECTURE.md#generated-files-and-local-outputs); no build artifacts or local-only assets are added.
- Includes, labels, citations, metadata ownership, and rights are correct.
- The checks required by [Contributing](CONTRIBUTING.md#validation-by-change-category) passed; unavailable checks are explained.
- Warnings and intentional limitations are stated.

## Release checklist

- Prepare the first or an increasing version on a development branch with
  `ashaiy book release --book <slug> --version <version>` and review its generated
  assembly changes in the normal PR.
- Confirm `build: true`. Enabling `release: true` requests first publication;
  subsequent releases require a version increase.
- Review the PR PDF before merging. Merging the release preparation authorizes
  automatic publication after main CI succeeds.
- Confirm the public release contains the versioned PDF and `SHA256SUMS`, and
  that its annotated tag points to the validated main commit.
- Preserve existing tags and assets. Recover failures through the original
  workflow's failed jobs using the
  [recovery procedure](#recovering-an-interrupted-release).

## Release publication

`build.yml` plans releases from the PR base or main push's `before` commit,
independently of the PDF snapshot baseline. It lists planned books, versions, and
tags in the job summary. Existing tags or failed tag lookups reject a PR plan;
publication checks again after merge. Release targets enter the PDF matrix even
if the snapshot has advanced. PRs only validate; manual **Build textbooks** runs
only refresh development PDFs.

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
  The retry validates the original main run and the source/strict-build gates of
  the attempt recorded in the package, even if failed jobs were retried later.
  It checks source ancestry, book version, artifact digest, and package metadata before
  granting publication write permission. It checks out the original source and
  publishes its retained bytes without rebuilding, even after main advances.
  A new **Build textbooks** dispatch does not recover old releases.
- If publication failed after packaging, retain the original `<slug>-release`
  artifact. Avoid rerunning successful build jobs: a rebuilt PDF can differ in
  bytes, and an existing immutable artifact must not be replaced.
- Re-enabling a previously published book does not reset its release history.
  Choose a higher version if its current version already has a tag.
- An existing tag must be annotated and point to the same validated commit.
  Every attempt pushes the validated tag without force before accessing the
  release, including retries with a local tag left by a rejected push. A tag
  push failure stops publication; retry after resolving the remote failure.
  Existing draft assets must match the original package byte for byte; only
  missing assets are uploaded. Conflicts stop publication without overwriting.
- An already-public release is downloaded and compared with the original package
  on retry. Missing or different assets fail verification without changing the
  release. If publication succeeded just before the job lost its connection,
  a retry with matching assets therefore completes safely.
- If a retained package has expired or conflicting bytes cannot be recovered,
  leave the draft unpublished and prepare a reviewed higher version. Never move
  an existing tag or overwrite public assets to force recovery.
- Automatic publication and manual retries share a queued lock per book, so
  they cannot upload the same release concurrently. All waiting versions are
  retained. A later main commit does not suppress an earlier version's publication.
  Main push runs have separate
  concurrency groups per commit; development snapshot writes remain serialized.
  If a run is cancelled or fails, recover that original run explicitly; later
  pushes do not implicitly backfill missed versions.

## Site publication checklist

Follow [Site metadata](site-metadata.md) for publication flags, generation,
validation, and styling. Confirm that generated pages remain untracked.

For initial setup:

1. In **Settings → Pages → Build and deployment**, choose **GitHub Actions** as
   the source. `configure-pages` checks the existing configuration; this workflow
   does not enable Pages or change repository permissions automatically.
2. If the `github-pages` environment has deployment branch restrictions, ensure
   `main` is allowed. Keep existing required reviews and other protection rules.
   The deployment job itself also accepts only `main`.
3. Push reviewed changes to main or dispatch **Build textbooks** on main. This
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

Snapshot writers retain queued runs with `queue: max`; older runs cannot evict a
waiting current-main publication. Before publishing, CI requires downloaded PDFs
to match the build matrix exactly. CI validates the complete site PDF set, prepares
replacements and removals in a temporary directory, then installs and pushes the
snapshot.
Missing or expired planned artifacts stop publication without advancing
`.source-sha`; run **Build textbooks** again to produce fresh artifacts. Missing
initial PDFs require a full **Build textbooks** run to bootstrap. Superseded main
runs exit before preparation, with main checked again before pushing.

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

Publication returns an immutable `snapshot_sha`; Pages uses that snapshot and
its recorded source, including manual or documentation-only retries. Deployment
jobs queue without cancelling one another. The deployment guard and artifact
checker are preserved before loading the snapshot's source. The snapshot is
checked before installing dependencies or rendering, and again immediately before
deployment. Superseded snapshots skip the build, upload, and deploy steps.
Before upload, the checker validates the actual rendered local links and PDF
bytes against the snapshot. The job has a 30-minute budget including dependency
installation, rendering, upload, and the deploy action's ten-minute timeout.
Remote/ref resolution failures stop deployment rather than count as a skip;
restore access or repair the ref, then retry. Main and the snapshot ref are not
locked as one transaction. These rules do not alter release packages.

## Drift detection

Use `ashaiy check source` for structural validation, `ashaiy report` for repository
health, and `ashaiy doctor book --book <slug>` for advisory book inspections.
Review shared changes against every affected consumer and preserve public interfaces.

## CI caches and verified PDF reuse

LaTeX formatting checks cache `.cache/latexindent/`. The source-check job sets
Python bytecode and Mathlib downloads to `.cache/python/` and `.cache/mathlib/`;
these directories are not separately restored by Actions.

Lean caches `.lake` by OS, architecture, toolchain, dependency lock, Lake
configuration, and Lean sources. LaTeX caches each book's `build/<slug>/` by OS,
architecture, image digest, and committed inputs from `books/<slug>/`, `common/`,
`config/`, and `scripts/`, with fallback only within the same book and image.
Shared directories are included conservatively; unrelated books, docs, and site
changes do not create new PDF cache entries. Cache hits run the normal build and
strict checks. GitHub cache scope means PR caches are generally unavailable to main. Only successful
main pushes save Lean and LaTeX caches; PRs restore them without creating
PR-scoped copies. Formatting cache keys include the Python implementations,
shell wrappers, and `config/latexindent.yaml`. CI runs
`python3 scripts/format_tex.py --check --prune-cache` to remove obsolete formatter
generations before saving. Locally, use this option only without concurrent
formatter runs; ordinary formatting preserves other generations and unknown
cache entries.

`scripts/github_artifacts.py` owns shared GitHub transport, successful-run
eligibility, run/attempt identity, and artifact digest checks. PDF, image, and
release modules retain their own file, size, and domain validation rules.

After a merge, each affected PDF job first looks for a successful `build.yml`
PR run for the merged PR's head in this repository. Reuse requires an identical
full Git tree (including workflows and build settings), image index digest,
platform, validation policy, run ID/attempt, and PDF/log checksums. The downloaded
archive must also match GitHub's artifact digest, and its log is strictly checked
again. GitHub commit trees are compared before artifact lookup and download.
A match skips the TeX container build and republishes the verified PDF as
the current run's artifact for snapshot publication.

Verified artifacts expire after 14 days. Missing, expired, mismatched, fork,
failed-run, or unavailable artifacts fall back to a normal cached build. Lookup
is bounded to 30 matching successful runs and 100 artifacts per run. Full-tree
matching is deliberately conservative: even an unrelated change after PR
validation can cause a rebuild. Merge, squash, and rebase do not need identical
commit SHAs when their final source trees match. A manual **Build textbooks**
dispatch skips PR reuse and builds every enabled book. Bump the cache versions
or `strict-pdf-v1` policy when their corresponding semantics change.

## Toolchain image operations

### Multi-platform toolchain images

Image builds restore architecture-specific `buildcache-<arch>` registry caches
and fall back to the latest image's inline cache. Non-PR builds export all
intermediate stages with `mode=max`; same-repository PR builders authenticate
with package-read access and only read registry caches. After a previously
published PR candidate reaches main, a cache-only build refreshes intermediate
stages without replacing the tested image.
This preserves the independent TeX Live installation across tool updates.

The package is `ghcr.io/sihyeon8240/ashaiy`. `build.yml` calls
`prepare-image.yml`, which derives a content tag and calls `build-toolchain.yml`.
Main waits for publication before using the immutable index. The manual
`build-image.yml` recovery workflow does not also run on pushes. Ordinary PRs resolve
the published tag for their inputs; `config/container-image.txt` remains the local
and Dev Container pin. Registry errors fail explicitly.

#### Validating an image PR

1. Both native runners must be available: `ubuntu-24.04` for AMD64 and
   `ubuntu-24.04-arm` for ARM64. Each candidate passes architecture and toolchain
   smoke checks; AMD64 also strictly builds every check-enabled textbook.
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
tree, run/attempt, archive checksums, image IDs, and architectures. It never
executes PR scripts or candidate containers with write credentials. Changed or
closed heads are skipped; mismatched merge trees require fresh CI.

Candidate downloads report bytes, average speed, and idle time every 15 seconds.
Download, extraction, and Docker load check available disk space with a 2 GiB
reserve. The gzip stream is measured before loading and capped at 40 GiB expanded.
They stop after 120 seconds without file growth and retry from zero up to three
times within a size-dependent budget per artifact: ten minutes plus transfer
time at 8 MiB/s, capped at one hour. Every completed
archive must still pass GitHub's digest and candidate provenance checks. Image
extraction, verification, loading, and publication log their stages; Docker push
output streams directly. Docker load and push each have ten-minute limits; the
publication job has a 180-minute overall limit. Publication code comes from
`main`, so these changes take effect there only after owner review and merge.

After publishing the index, the publisher adds one commit changing only
`config/container-image.txt` and `.devcontainer/devcontainer.json` to the original
PR branch. An isolated index and exact-head push lease protect concurrent author
changes. Retries skip applied pins. The destination comes from trusted main
configuration; no separate pin PR or branch is created.

After pushing a pin with `GITHUB_TOKEN`, the publisher dispatches **Build
textbooks** on the PR branch with the exact expected commit. Dispatch events run
automatically without a GitHub App, PAT, or approval of the separate PR-event run.
The source gate rejects a dispatch if the branch moved before it started. Final
consumer CI resolves the published image and does not trigger another publisher.
If dispatch fails, manually dispatch **Build textbooks** on the PR branch with
`expected_sha` set to the pin commit; do not rerun CI on the pre-pin commit.
Ordinary textbook PRs neither publish images nor update pins.

The content tag hashes inputs and build policy from `config/image-build.json`.
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
