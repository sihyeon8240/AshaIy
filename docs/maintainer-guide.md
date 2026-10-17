# Maintainer guide

Use [the architecture guide](ARCHITECTURE.md) for repository structure and
ownership, and the [documentation map](README.md) to find task-specific policies.

## Reviewing changes

Confirm scope, ownership, mathematical correctness, provenance, labels,
bibliography, generated files, and reported validation. AI-generated changes
require the same review plus checks for invented citations, broad rewrites,
unsupported claims, and changes that merely look plausible. Risk is highest in
mathematical content, `common/styles/`, metadata/versioning, scripts, workflows,
templates, and any repository-wide rename.

## Safe changes

For shared styles, metadata, images, scripts, and templates, follow the ownership
policy in the [architecture guide](ARCHITECTURE.md), the
[validation requirements](CONTRIBUTING.md#validation-by-change-category), and the
operational commands in the [developer workflow](developer-workflow.md). Preserve
public interfaces and test every affected consumer.

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

`build.yml` compares the PR base or the main push's `before` commit with the
checked-out manifest, independently of the development snapshot baseline.
PR planning queries the base repository for existing release tags and rejects
reusing any planned tag; lookup failures fail the check. The Actions job summary
lists planned books, versions, and tags for PRs and main pushes. This early check
does not reserve tags; publication still checks for conflicts after merging.
Release books are included in the PDF build matrix even if the snapshot has
already advanced. PRs validate the plan without publishing. Ordinary manual
**Build textbooks** runs refresh development PDFs only.

After the main source, Lean, formatting, and strict PDF gates pass, `build.yml`
calls `release.yml` with the release book matrix. The build jobs package the
strictly checked PDFs, `SHA256SUMS`, and `release-build.json` into `<slug>-release`
artifacts retained for 90 days. The metadata binds the package bytes to the book,
version, source commit, run ID, and attempt. Publication uses those same-run
packages and tags the exact validated `GITHUB_SHA`. Pages deployment and
versioned releases are independent consumers of the validated build.

Each publication creates an annotated `<slug>-v<version>` tag, stages a draft,
uploads `<slug>-v<version>.pdf` and `SHA256SUMS`, downloads and verifies both, then
automatically publishes the draft. Versions with a prerelease suffix are marked
as prereleases. Releases use their book tag as the title; GitHub-generated notes
are repository-wide. No book claims the repository-wide `Latest` designation.
The release process does not change the descriptive book `status` in `config/books.yml`.
Only publication jobs receive repository-content write permission for releases.

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

PDF publication separates preparation from Git transport:

| State | Action and failure behavior |
|---|---|
| Current-main check | A superseded run exits before preparation; main is checked again just before the push. |
| Plan | Validate registered update slugs, nonempty artifacts, and the complete site PDF set before changing existing PDFs. Missing PDFs require a full build to bootstrap the snapshot. |
| Prepare | Copy the current set into a temporary directory, replace updated site books, and prune retired/non-site PDFs there. Copy failures leave the existing set available. Unchanged sets need no copy. |
| Install | Replace the PDF directory; on installation errors or a Python cancellation exception, restore the previous directory. If restoration fails, retain its path in the error message for recovery. |
| Publish | Only after preparation succeeds, write source metadata, commit, and push the snapshot. Git/network failures remain failures rather than successful publication results. |

Temporary preparation lives under the snapshot worktree as `.pdf-staging-*`
and is removed on success or successful rollback. If rollback itself fails,
its `previous/` directory retains the old PDFs; restore it as that worktree's
`pdf/` directory before manual recovery. Abrupt process termination is not a crash-safe
transaction: inspect any retained staging directory before local reuse.
These local preparation rules do not change release packages or Pages gating.

Git transport uses a separate temporary worktree for each attempt. Normal
successes and failures remove it and its attempt-owned bootstrap branch;
restoration failures retain the recovery worktree and print its path. A retry
starts from the remote snapshot again, so a failed attempt's directory or local
commit does not block it. Publication identity is passed to the commit command
without changing the source checkout's Git user configuration.

Only `git ls-remote --exit-code` status 2 authorizes initializing an absent
snapshot branch. Lookup/transport errors remain failures. Likewise, only status
1 from the staged diff authorizes creating a changed snapshot commit. Normal
fast-forward pushes reject concurrent snapshot changes, which can be retried
against a freshly fetched snapshot. Even an unchanged snapshot is pushed before
success outputs are written; a retry after a completed publication returns its
existing commit. The final main check reduces superseded writes but does not
lock main and the snapshot ref as one transaction.

Snapshot publication returns its immutable `snapshot_sha`. Pages checks out that
commit and its recorded source rather than rereading a moving branch. Manual or
documentation-only deployment retries resolve the current snapshot once. Pages
jobs queue without cancelling each other; just before deployment they compare the
selected snapshot with the current branch and skip superseded snapshots. A delayed
older job therefore cannot cancel or overwrite a deployment already made from a
newer snapshot. The deployment guard is loaded before checking out the snapshot's source.
Fetch or snapshot commit-resolution failures stop deployment with an error and
emit no `current` result; only a successful comparison can skip an older snapshot.
Retry the deployment after restoring remote access or repairing the snapshot ref.

## Drift detection

Run `ashaiy check source` for structural validation, `ashaiy report` for repository
health, and `ashaiy doctor book --book <slug>` for advisory textbook inspections.
Check that changes follow the architecture contract. Before
changing common styles, scripts, or templates, document the motivation, test
every consumer, preserve interfaces, and provide a rollback-sized diff.

## CI caches and verified PDF reuse

LaTeX formatting checks cache `.cache/latexindent/`. The source-check job sets
Python bytecode and Mathlib downloads to `.cache/python/` and `.cache/mathlib/`;
these directories are not separately restored by Actions.

Lean caches `.lake` by OS, architecture, toolchain, dependency lock, Lake
configuration, and Lean sources. LaTeX caches each book's `build/<slug>/` by OS,
architecture, image digest, and source tree, with fallback only within the same
book and image. Cache hits run the normal build and strict checks. GitHub
cache scope means PR caches are generally unavailable to main. Only successful
main pushes save Lean and LaTeX caches; PRs restore them without creating
PR-scoped copies. Formatting cache keys include `config/latexindent.yaml`.

`scripts/github_artifacts.py` owns shared GitHub transport, successful-run
eligibility, run/attempt identity, and artifact digest checks. PDF, image, and
release modules retain their own file, size, and domain validation rules.

After a merge, each affected PDF job first looks for a successful `build.yml`
PR run for the merged PR's head in this repository. Reuse requires an identical
full Git tree (including workflows and build settings), image index digest,
platform, validation policy, run ID/attempt, and PDF/log checksums. The downloaded
archive must also match GitHub's artifact digest, and its log is strictly checked
again. A match skips the TeX container build and republishes the verified PDF as
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

`build.yml` prepares the toolchain before formatting and PDF checks. On main,
it calls `prepare-image.yml`, waits for image validation and publication, and
passes the resulting immutable index to every consumer. This also bootstraps
the first push without a pre-existing registry image or a manual pin update.
Ordinary PRs resolve the content-addressed tag for their image inputs to an
immutable index; `config/container-image.txt` remains the development-container
pin. Registry errors fail explicitly. Verified-PDF reuse is bound to the actual
registry image and full source tree.

The image package is `ghcr.io/sihyeon8240/ashaiy`.

For image-input and image-pipeline PR changes, `build.yml` calls the separate
`prepare-image.yml` pipeline through its read-only `image-validation` job. Its
tested AMD64 image is passed to both formatting and textbook jobs. When the
image is not published yet, consumers download the run-local artifact, verify
its image ID and architecture, and run it without pulling from the registry.
Candidate failure blocks consumers and the required **Check sources** gate.
Ordinary textbook PRs skip candidate building. `build-image.yml` remains available
for independent publication and manual recovery; content-tag concurrency prevents
duplicate builds when it overlaps main CI. `prepare-image.yml` derives the content tag and calls
`build-toolchain.yml`. Both native runners must be available: `linux/amd64` uses
`ubuntu-24.04`, and `linux/arm64` uses `ubuntu-24.04-arm`. Each candidate passes
architecture and toolchain smoke checks; AMD64 also builds every checked textbook
and strictly checks the logs before its candidate can be published or archived.

Same-repository PR jobs may authenticate to GHCR with package-read permission;
fork PRs use anonymous registry access. PR jobs never publish images. They preserve both architecture
archives for 14 days, with image IDs, archive checksums, source tree, and run
identity. After successful PR CI, `pin-pr-image.yml` runs trusted code from main
with publication permissions. It accepts only open, same-repository PRs targeting
main whose current head matches the successful `build.yml` run. Fork PRs remain
read-only; a maintainer must bring an image change into a same-repository PR to
publish and pin it. Same-repository Dependabot PRs use the same promotion path.

The publisher reads the current PR merge tree as data, verifies both artifacts'
availability and GitHub digests, then checks each manifest's policy, tree, run
attempt, checksum, image ID, and architecture before pushing it. It never checks
out or executes PR scripts or runs candidate containers with write credentials.
A moved merge tree fails artifact verification and requires fresh PR CI. A changed
or closed PR head is skipped. Missing or expired candidates require rerunning PR CI.

The content tag hashes the Dockerfile, toolchain configuration, toolchain check,
platform list, and build policy version. Bump the policy version when changing
build or validation semantics that require a fresh image. Existing tags are reused
only if their index includes both Linux platforms; incompatible tags fail without
being overwritten. Registry errors never authorize a build. Final index publication
is serialized between main and PR publishers, with a registry recheck after waiting.
Temporary per-architecture tags may remain after a partial publication failure.

After publishing the verified index, the publisher appends one commit changing
only `config/container-image.txt` and `.devcontainer/devcontainer.json` to the
original PR branch. An isolated Git index prepares the commit without checking
out PR code, and an exact-head push lease rejects concurrent author updates,
branch deletion, or rewinds. Retries skip pins already applied. The publication
destination comes from trusted main configuration.

Run-local candidate PDFs are not recorded for registry-digest PDF reuse; the
consumer run after pinning uses the published index and can record reusable PDFs.
Wait for the pin commit and its final consumer CI before merging an image PR.
PRs updated with `GITHUB_TOKEN` require a maintainer to select **Approve workflows
to run** in the PR merge box before the new CI runs. See
[GitHub's token event rules](https://docs.github.com/en/actions/concepts/security/github_token#when-github_token-triggers-workflow-runs).
The pin commit does not change image inputs; subsequent validation reuses the
published tag and promotion makes no further commit. Ordinary textbook PRs do
not publish or update image pins.

`build-image.yml` handles main publication and manual recovery without creating
follow-up PRs or updating main directly. Dispatch it on main to recover a missing
image, then update the pin in a development PR with `ashaiy image pin --digest <sha256>`.

Initial main CI publishes and consumes its own image automatically, including
when the new GHCR package is private. Main and same-repository PR consumers
authenticate with package-read permission. Existing packages must grant this
repository Actions access. CI does not change package visibility, repository
permissions, or the development-container pin on main.

For fork PRs or unauthenticated local pulls, make the package public in its GHCR
settings. Public repository visibility does not make a new package public.
This is unnecessary for initial main CI and same-repository PRs.

For manual recovery or updating a development-container pin after moving a
repository, use this order:

1. Dispatch **Validate and publish toolchain image** (`build-image.yml`) on main.
   Publisher jobs log in with `GITHUB_TOKEN` before checking existing tags,
   including the serialized publication recheck. The token needs package write
   access; an existing package must grant this repository Actions access.
   An explicit missing manifest permits a build. A denied lookup still fails
   rather than treating an inaccessible immutable tag as absent.
2. After publication, set the GHCR package visibility to **Public** in its package
   settings if anonymous pulls or fork PRs are needed. New packages default to
   private; fork PRs intentionally pull without registry credentials. See
   [GitHub's container registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
3. Resolve the published index with
   `docker buildx imagetools inspect ghcr.io/sihyeon8240/ashaiy:latest`
   from an unauthenticated Docker configuration. On a development branch, run
   `ashaiy image pin --digest <sha256>` with that index digest and submit the
   synchronized pin changes in a PR. A pin copied from another registry or a
   previous repository is not evidence that the image exists at the new location.
4. Run consumer CI. Main CI waits for its own image preparation, and ordinary
   PR CI resolves the published image for the current image inputs. Updating the
   development-container pin is not a prerequisite for these consumers.

For an open PR, rerun its CI to retry automatic publication and pinning. If it
was merged before pinning, include the recovered pin in a subsequent development
PR. Dispatches on other branches do not publish. Dependabot groups Docker and
GitHub Actions updates into one weekly infrastructure PR.

Image preparation holds a content-tag concurrency group across the registry
check, native builds, and publication. The group uses `cancel-in-progress: false`
and `queue: max` to preserve waiting runs. Main can still reuse matching successful
same-repository PR artifacts after merge if publication is needed; unavailable
candidates fall back to building from source. PR publication itself never rebuilds
source with write credentials.

`scripts/ci_changes.py` owns changed-path discovery and common consumer facts;
source CI uses the PR/event baseline, while cumulative PDF planning uses the
snapshot baseline. Image push path filters are synchronized by `ashaiy config generate`.
Image hashing, build-matrix selection, and index architecture selection read
`config/image-build.json` at runtime through `scripts/image_policy.py`; changing
those values does not regenerate the preparation/build workflows. Trigger
filters remain generated because GitHub needs them before any job can run.
The helper uses only Python's standard library. Review the policy version
when changing hash or build semantics.
Source checks skip Lean setup, compilation, and cache transfers for documentation,
consumer pin/configuration changes, and workflow edits limited to artifact Action
pins.
Proof-link scanning, repository checks, formatting, unit tests, and workflow
validation remain enabled. Dockerfile, toolchain, proof, and unknown changes keep
Lean checks; manual dispatches and unavailable diff bases also run them.

Set the repository's default workflow token permissions to read-only. Workflows
declare the write permissions needed for image publication, PR branch commits,
snapshots, Pages, and releases explicitly. No automatic approval or merge steps
are used. There are no bot-created pin PRs or dedicated image-pin branches.
Use the repository's **Automatically delete head branches** setting for merged
PRs; there is no separate branch-deletion workflow.

Digest and candidate artifacts expire after 14 days. Temporary
`build-<run>-<attempt>-<arch>` registry tags are retained, including when the other architecture fails; final
image tags are published only after both smoke tests pass. See the
[Docker multi-platform CI guide](https://docs.docker.com/build/ci/github-actions/multi-platform/).

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

The image includes Jekyll and Ruby/Bundler for local site rendering, Chromium
and ChromeDriver for browser layout tests, Poppler utilities (`pdfinfo`,
`pdftotext`, `pdftoppm`) for PDF inspection, and `jq` for JSON inspection.
These tools and Ruby dependencies use Debian Bookworm packages. Jekyll and
Bundler upstream versions are checked against `config/toolchain.env`.
Chromium and ChromeDriver must have identical Debian package versions.
Debian package revisions, including browser, Poppler, and jq updates, follow
Bookworm updates.

The reviewed image digest pins the installed dependency set. Rebuilding the
Dockerfile can pick up newer Debian revisions.

For package updates, change `config/toolchain.env` first and regenerate
`.github/requirements-ci.txt` with `ashaiy config generate`; update tool binary checksums
for both architectures when their versions change. Validate dependency updates
with the complete suites required by the contributing guide.
