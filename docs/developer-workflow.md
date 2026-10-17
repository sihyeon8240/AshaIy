# Developer workflow

This guide describes ordinary repository operations.
[The architecture guide](ARCHITECTURE.md) is authoritative for structure
and metadata ownership.

## Development environment

The publishing compiler is LuaLaTeX through `latexmk`. Tool versions are owned by
`config/toolchain.env`. The reviewed local and devcontainer image pin lives in
`config/container-image.txt`. CI selects the image for its current image inputs:
main prepares and publishes it before consumers run, ordinary PRs resolve its
published content tag to an immutable digest, and image-changing PRs use the
tested candidate directly for formatting and PDF checks.
Lean consumes the synchronized `lean/lean-toolchain` and locked Mathlib dependency.

Follow the root [quick start](../README.md#quick-start) to open the supported
development container. For Linux or WSL2 host installation, follow
[local development](local-development.md). `ashaiy doctor env` checks PDF tools;
use `--profile lean`, `--profile format`, or `--profile site` for optional tasks,
and `--profile full` for the pinned container toolchain.
After changing shared configuration, run `ashaiy config generate` and `ashaiy config check`.

The image includes the tools for PDF builds, Lean checks, formatting, and local
site previews. See [Local preview](site-metadata.md#local-preview) for site commands
and [Toolchain updates](maintainer-guide.md#toolchain-updates) for dependency
maintenance.

## Daily development workflow

From the repository root, check the environment and build the book you are editing:

```sh
ashaiy doctor env
ashaiy book build --book linear-algebra --check --strict
```

Replace `linear-algebra` with the book's slug from `config/books.yml`. Select the required
pre-review checks from [Contributing](CONTRIBUTING.md#validation-by-change-category).

### Inspecting change impact

From the repository root, inspect committed changes without running checks or
publishing anything:

```sh
python3 scripts/repository_cli.py plan \
  --source-base <event-base-sha> \
  --pdf-base <snapshot-source-sha>
```

Use the PR/event comparison base for source checks. On main, use the last PDF
snapshot's `.source-sha` for cumulative PDF planning; this can precede the
event base when earlier changes have not been published. The command does not
fetch or discover that remote snapshot. Omitted, missing, or invalid bases
conservatively select the corresponding checks/builds. An empty valid diff
selects no consumers unless an explicit release build is requested.

The JSON result includes the resolved HEAD, source/PDF comparisons, selection
reasons, and `working_tree_dirty`. Diffs cover committed changes through HEAD;
metadata and dependencies come from the current checkout. Use a clean checkout
for a CI-equivalent plan.

Repeat `--release-book <slug>` to include build-eligible release targets.
The command explains selection; it does not determine release eligibility or
run validation. See [automation ownership](ARCHITECTURE.md#repository-automation-modules)
for the implementation.

### Working branches

Keep local `main` synchronized with `origin/main` using fast-forward updates.
Never commit or push directly to `main`; remote changes enter through pull
requests. Create `local-work` from the synchronized `main` and accumulate
focused, independently revertible commits there. Sequential requests may share
this branch and one manageable batch PR. Separate large or risky changes, or
changes likely to be deferred independently, into their own branches and PRs.

Validate the combined batch before review. The repository owner reviews and
merges the PR after the required GitHub Actions checks pass. After the merge,
fast-forward local `main` to `origin/main` and recreate `local-work` from it for
the next batch. Before removing the old branch, confirm that all work was
included in the merge or preserved elsewhere. Start with fresh branch history
after a squash merge to avoid carrying already merged commits into the next PR.

### Build outputs

CLI build files stay under the ignored `build/` directory, while LaTeX
Workshop writes to the ignored `vscode-build/` directory. Release packages are
retained as GitHub Actions artifacts.

Both build paths use the same LuaLaTeX configuration, shared TeX search paths,
and failed-build cleanup. Successful PDFs remain available for incremental
builds; a compiler failure or interruption removes that build's PDF. Strict
checks inspect the build log on every invocation, including incremental builds.
Shell escape is opt-in: use `ashaiy book build --book <slug> --shell-escape`, or select
the corresponding LaTeX Workshop recipe.

## CLI command interface

`ashaiy --help` lists commands; append `--help` at any level for options.
The executable is `scripts/ashaiy`, backed by Python's standard-library argparse.
Make compatibility is intentionally absent.

Toolchain images install a small launcher at `/usr/local/bin/ashaiy`. It invokes
`$ASHAIY_ROOT/scripts/ashaiy`; `ASHAIY_ROOT` defaults to `/workspace` in the image
and is set to the actual checkout path by the Dev Container and Docker runner.
CLI source stays in the checkout, so edits do not require rebuilding the image.
The scripts directory itself is not added to PATH.

For existing pinned images, `scripts/setup-cli.sh` creates a launcher symlink in
`.cache/bin/`; the Dev Container and Docker entry point add only that directory
to PATH. Rebuild/reopen the Dev Container after changing its configuration.
From a host checkout, invoke `./scripts/ashaiy` directly; Python 3 and the
repository's Python dependencies are required. The Docker runner can be invoked
as `./scripts/run-container.sh` without those Python dependencies on the host.

The image omits system GCC/G++, Make, development headers from `build-essential`,
Tk GUI tools, and `patch`. Lean's bundled Clang and native libraries remain
available for native compilation. PyYAML is installed from a binary wheel;
Ruby/Jekyll and TeX use their packaged tools. Image CI builds the Mathlib cache
executable in a fresh Lean workspace on each supported architecture.

Commands work from any checkout subdirectory. Repository operations use the
checkout root; relative `--file` paths resolve from the caller's directory.
`--book` accepts a registered slug, its `label_prefix` (`la`, `ma`, `ent`), or a
unique slug prefix. Exact slugs take precedence; ambiguous or unknown selectors
fail before any operation starts. Book omission follows the registry flags:
build uses `build: true`, build with `--check` uses `check: true`, and generation
selects all books (site generation selects site-enabled books).

```sh
ashaiy book list
ashaiy book build --book la --check --strict
ashaiy book build --jobs 4
ashaiy book new --slug example --title "Example"
ashaiy book release --book la --version 0.2.0
ashaiy contents generate --book la
ashaiy contents check --scope sections --book la
ashaiy generated generate
ashaiy generated check
ashaiy config generate
ashaiy config check
ashaiy lean build
ashaiy lean check
ashaiy check source
ashaiy check all --strict
ashaiy test
ashaiy doctor book --book la
ashaiy report
```

`book build --strict` requires `--check`; it treats log warnings as failures.
`--shell-escape` explicitly enables TeX shell escape for that build.
`generated` processes Lean aggregation, LaTeX assembly, and enabled site pages;
a selected site-disabled book skips only the site step. Explicit `site generate
--book` requires a site-enabled book. Generation and full checks stop at the first
failed stage; earlier generation stages may already have written their outputs.
The full check includes formatting, Lean, and PDFs; Python tests are separate.

The CLI preserves operation exit statuses, reports usage errors with exit 2,
missing executables with exit 127, and interrupts with exit 130. It does not invoke
a shell to interpret option values. `image run --command` deliberately passes one
command string to Bash inside the container.

Bulk builds use bounded concurrency; `--jobs` overrides `BOOK_BUILD_JOBS`.
Without either, the worker count defaults to `min(4, CPU count, selected books)`.
Output is buffered per book, and failures are aggregated after all workers finish.

## Terminal containers

Docker and Python 3 with PyYAML on the host are enough to use the toolchain without VS Code:

```sh
ashaiy image run
ashaiy image run --command 'ashaiy book build --book linear-algebra --check --strict'
ashaiy image build
ashaiy image run --image ashaiy-toolchain:local --command 'ashaiy test'
```

`ashaiy image run` defaults to the reviewed image in `config/container-image.txt`.
`ashaiy image build` builds the current Dockerfile for the host architecture and
uses the local tag `ashaiy-toolchain:local`; use `--image <tag>` to choose another tag.
Building does not change the reviewed pin. `ashaiy image pin --digest <sha256>` is
reserved for the reviewed
[image publication and pinning procedure](maintainer-guide.md#multi-platform-toolchain-images).

The run command mounts the repository at `/workspace`, sets the shared TeX search
paths, and uses the host UID/GID so generated files retain the host user's
ownership. It opens zsh by default or executes `--command` with Bash and returns its exit
status. A terminal
is allocated only when both input and output are terminals; piped input is kept.
`--command` is passed as one string, so quote it to prevent host-shell expansion.

The container gets a writable home under
`${XDG_CACHE_HOME:-$HOME/.cache}/ashaiy-container/<repository-id>` on the host.
This is persistent home state, including Elan settings and installed toolchains,
not a disposable tool cache. It and Mathlib's `lean/.lake` directory survive
subsequent runs and `ashaiy clean build`. The numeric container user
reuses the image's installed Lean toolchains and can download a newer pinned
toolchain into its writable home. It starts a plain zsh session rather than
root's personal shell configuration. Host Git/SSH credentials and the Docker
socket are not mounted automatically. Docker must run locally with access to the
checkout and cache paths. On Docker Desktop, allow sharing those directories.

## VS Code tasks and authoring support

Use **Run Build Task** for the selected textbook and **Run Test Task** for the
Python suite. **Run Task** also exposes strict book validation, Lean checks,
focused repository checks, generated-content updates, environment inspection,
and formatting of the current file. Tasks invoke the public `ashaiy` interface.
Book selection comes from `config/books.yml`; run `ashaiy config generate` after changing that
manifest and commit the synchronized `.vscode/tasks.json`.

LaTeX Workshop's default recipe provides a quick PDF preview. Choose a
**strict validation** recipe to run the repository log checker after compiling,
or run the strict book Task. Preview compilation alone does not establish that
references, citations, and overfull boxes satisfy the repository checks.
Task matchers connect LaTeX, Lean, Ruff, log-checker, and formatting diagnostics
to the Problems panel where their output supplies file locations. Other
diagnostics remain available in the task terminal.

The Test Explorer discovers `unittest` cases under `tests/`. Local JSON schemas
under `config/schemas/` provide YAML completion and structural validation for
book, chapter, section, and Lean module manifests. Python repository checks
remain authoritative for duplicate names, referenced files, balanced TeX titles,
and other semantic constraints. Keep schemas aligned with the manifest parsers.
Build outputs and caches are excluded from VS Code file watching and search;
source files retain their normal watching behavior.

`.vscode/extensions.json` owns extension recommendations. `ashaiy config generate`
synchronizes them into the Dev Container installation list, and
`ashaiy config check` detects drift in both editor lists.
The Dev Container also selects `/usr/local/bin/ruff` explicitly so editor
formatting uses the installed toolchain version.

## Cleaning outputs and caches

Run `ashaiy clean source` to remove disposable files outside `build/` and
`vscode-build/`, including LaTeX auxiliary files, `latexindent` logs, patch
backups/rejects, editor backups and swap files, and an interrupted manifest
write's temporary file. The command deliberately preserves `build/tree.txt`, build
output, formatter caches, Python caches, and Lean's `.lake` directory. These
artifact names are also excluded from Git and from `ashaiy tree` output.

Use `ashaiy clean build` to remove generated CLI and VS Code build output. Local
tool caches are preserved unless explicitly selected with
`ashaiy clean cache --scope {lake|mathlib|tex|ruff|py|all}`.

| Scope | Default location | Contents |
|---|---|---|
| `tex` | `.cache/latexindent/` | Successful LaTeX formatting checks |
| `ruff` | `.cache/ruff/` | Ruff formatter and lint caches |
| `py` | `.cache/python/` | Python bytecode |
| `mathlib` | `.cache/mathlib/` | Mathlib downloads |
| `lake` | `lean/.lake/` | Lean dependencies, configuration cache, and build results |

The CLI sets absolute `PYTHONPYCACHEPREFIX` and `MATHLIB_CACHE_DIR` defaults.
The devcontainer and `ashaiy image run` set these variables inside the container
as well, so direct Python and Lake commands there use the same locations.
`scripts/check-lean.sh` also sets defaults when invoked directly. Ruff reads its
cache path from `config/pyproject.toml`; the LaTeX formatter sets its own default.

For direct Python or Lake commands in a host shell, set these variables from the
repository root first (Python must see its setting before it starts):

```bash
export PYTHONPYCACHEPREFIX="$PWD/.cache/python"
export MATHLIB_CACHE_DIR="$PWD/.cache/mathlib"
```

Explicit environment overrides are respected by the CLI; the container runner uses
container paths rather than forwarding host paths. `FORMAT_TEX_CACHE_DIR` and
`RUFF_CACHE_DIR` can also override the formatter defaults. Cleanup only targets
the repository's default locations, never arbitrary override paths or shared
user caches.

Cleanup rejects symbolic links at the cache directory or its immediate parent
so it cannot traverse a redirected cache root. Use `all` to remove all listed
categories; unknown directories under `.cache/` are preserved.
The persistent container home is excluded, and `mathlib` does not remove
`lean/.lake/`. Avoid cleaning caches while their tools are running.

## Formatting

Shared VS Code settings live in `.vscode/settings.json`, with extension
recommendations in `.vscode/extensions.json` and formatting tasks in
`.vscode/tasks.json`. The devcontainer installs those extensions and keeps
container-specific terminal settings. Outside the container, install the tools
at the versions in `config/toolchain.env`.

Python, LaTeX, and shell documents format on save. Python also applies safe Ruff
fixes and import organization on explicit saves. Shell formatting uses the same
Bash variant and two-space indentation as the CLI. LaTeX Workshop sends its
buffer through `scripts/format-tex-file.sh`, which returns formatted text without
modifying the input. The CLI calls the same helper and owns file selection and
caching. New TeX files are formatted by the editor before staging; repository-wide
TeX commands without `--file` select only tracked files. Edit generated
assembly through its manifests and generators.

EditorConfig preserves Markdown trailing spaces, including hard line breaks.
VS Code also disables trailing-space trimming for Markdown. Saving removes extra
final blank lines and inserts the final newline.

Use the CLI commands for repository formatting:

```sh
ashaiy format tex
ashaiy format py
ashaiy format sh
ashaiy format all
ashaiy format tex --check
ashaiy format py --check
ashaiy format sh --check
ashaiy format all --check
ashaiy format tex --file "books/mathematical-analysis/chapters/basic-topology/draft.tex"
ashaiy format py --check --file scripts/books.py
ashaiy format sh --file scripts/build-book.sh
```

The task layer runs the selected formatters; `all` runs TeX, Python, shell, then
repository-wide newline normalization, stopping at the first failure. Formatter
exit statuses are preserved, and file paths are passed as literal arguments.

Without `--check`, the selected formatter updates files in place. With `--check`, it
only reports drift and exits unsuccessfully when a file needs formatting. Review
the resulting diff: formatting is mechanical and does not replace mathematical or
code review.

`--file <path>` selects exactly one existing source, including an untracked draft,
for a single `tex`, `py`, or `sh` scope. Relative paths are resolved from the
invocation directory; absolute paths and paths containing spaces also work.
The file must be inside this repository, not ignored by Git, and have a matching
extension (`.tex`/`.sty`, `.py`, or `.sh`). `--file` cannot be combined with `all`.
The current-file Tasks use this same interface; save the file before running a
Task because CLI formatting reads the file on disk.

All formatter targets require their text files to end with exactly one LF.
`ashaiy format all` additionally applies that end-of-file rule to every non-empty,
Git-tracked text file; binary and untracked files are excluded. The complete
check applies the same repository-wide validation.

The LaTeX formatter is `latexindent`, configured in `config/latexindent.yaml`.
It processes every Git-tracked `*.tex` and `*.sty` file, including book sources,
shared styles, and templates, with two-space indentation. Prose and explanatory
comments wrap to 88 columns after indentation, and environment beginnings, bodies,
and endings start on separate lines. Manual line breaks are preserved, and
`aligned` environments align both `&` delimiters and trailing `\\`. Sentences
do not have to start on separate lines. Consecutive blank lines are condensed to
one. A final indentation-only pass corrects indentation after prose wrapping.

The column width is a wrapping target, not a hard limit: verbatim code and
unbreakable tokens can remain longer. Lean environments retain their relative
code indentation. Generated boundary comments, Lean source references, editor
directives, and empty `%` section markers are protected from comment wrapping.
Untracked drafts and other extensions are not included. Temporary
`latexindent` files are isolated and removed automatically. The command fails
with a dependency error when `latexindent` is not available.

Review formatter diffs because `latexindent` recognizes TeX structure
heuristically.

Python formatting applies only to `scripts/` and `tests/`. Update mode applies
the configured safe Ruff fixes and formatting; check mode is non-mutating.
`config/pyproject.toml` owns formatter and lint policy, while
`config/toolchain.env` owns the Ruff version synchronized into
`.github/requirements-ci.txt` by `ashaiy config generate`.

Shell formatting applies `shfmt` with the Bash language variant and two-space
indentation to `scripts/*.sh`. ShellCheck and `bash -n` remain the semantic and
syntax checks; formatting does not replace either check.

`ashaiy check source` runs structural checks, documentation checks, `bash -n`,
and ShellCheck at error severity. It requires ShellCheck and ripgrep, but runs
no formatter and needs neither a TeX installation nor Ruff.
`ashaiy check docs` checks local Markdown links and heading anchors plus the
documented theorem-environment list against the shared style, without network
access or TeX. It does not verify prose claims or external URLs.
Source CI invokes Python, shell, and LaTeX formatting checks. The complete
`ashaiy check all [--strict]` command includes all three gates before
checking proofs and building books. Use the focused
`ashaiy format {tex|py|sh|all} --check` commands when a full build is unnecessary.

## Review

Follow the [contribution requirements](CONTRIBUTING.md#pull-requests) when preparing
review. Include affected books, validation results, unresolved warnings, and
unavailable local-only assets. Reviewers use the
[maintainer checklist](maintainer-guide.md#pull-request-checklist).

## Project logo

`common/styles/logo.sty` defines the `\AshaIy` wordmark placed at the
upper right of the copyright page by the shared `common/templates/cover.tex`
template. The website uses a tracked SVG export with outlined glyphs, so it does
not require visitors to install the font.
After editing the macro, regenerate the website artwork from the repository root:

```sh
mkdir -p build/logo
TEXINPUTS=.:common/styles//: lualatex -interaction=nonstopmode -halt-on-error \
  -output-directory=build/logo common/templates/artwork.tex
dvisvgm --pdf --no-fonts --exact-bbox --output=site/assets/ashaiy-logo.svg \
  build/logo/artwork.pdf
scripts/normalize-eof.sh site/assets/ashaiy-logo.svg
```

Commit the LaTeX sources and synchronized SVG; PDF and auxiliary files stay in
ignored `build/logo/`. Review the covers and site header after regeneration.

## CI and publication

### Continuous integration

CI validates repository sources, formatting, tests, Lean proofs, affected PDFs,
and site output. Shared and ambiguous build inputs select every build-enabled
book; book-local changes select only their affected consumers. The workflow
definitions under `.github/workflows/` are authoritative for job structure,
permissions, concurrency, and publication implementation.

`build.yml` owns PR and main CI, including the **Check sources** and
**Verify textbook builds** status checks. Source checks and affected-book planning
start independently. Main CI waits for image preparation and publication, including
on the first push. Image changes invoke a candidate pipeline included in
**Check sources**, then formatting and PDF jobs consume that tested image using
run-local artifacts when necessary. Ordinary PRs use the published immutable index
for their image inputs. Eligible PR archives can be reused for publication after
merge. The [maintainer guide](maintainer-guide.md#multi-platform-toolchain-images)
explains image publication and which changes require Lean setup and compilation.

Cache restores run normal validation. After a merge, CI may reuse a
verified PR artifact when its full source tree and build environment match;
otherwise it builds the affected PDF normally. See the
[maintainer guide](maintainer-guide.md#ci-caches-and-verified-pdf-reuse) for cache
boundaries, artifact eligibility, and rebuild procedures.

### Development PDF snapshots

Successful `main` builds maintain the development PDF snapshot used by Pages.
Maintainers can bootstrap or safely rebuild that snapshot by manually dispatching
**Build textbooks**, which selects every build-enabled book. Pull requests and
fork pull requests do not publish.

**Deploy static site** checks out the source commit recorded in the downloaded
PDF snapshot's `.source-sha`, including for manual dispatches. Calls from the
build workflow after a snapshot update must match that commit, so a newer
snapshot cannot be mixed with an older source checkout. The caller passes the
immutable snapshot commit; superseded deployments are skipped before publication. Successful main checks
also retry deployment when no snapshot update is needed, using the existing
snapshot and its recorded source. This recovers a failed deployment after a
subsequent documentation-only change without rebuilding PDFs. To publish new
source changes, run **Build textbooks** first; deploying the site alone
republishes the recorded snapshot.

### Releases

A reviewed `release: false` to `release: true` change requests publication of
that book's current version, so a first release can use `0.1.0` unchanged. A newly
registered book with `release: true` also requests its first publication. While
`release: true` remains set, only a version increase requests another release;
ordinary content changes do not. Version changes must increase in semantic-version
order. Release targets must also have `build: true`. A version change while
`release: false` does not publish. Check `config/books.yml` for each book's settings.

On `local-work` or another development branch, run:

```bash
ashaiy book release --book mathematical-analysis --version 0.1.0
```

This enables `release: true`, sets that book's version in `config/books.yml`, and
synchronizes its generated assembly, equivalent to `ashaiy contents generate --book <slug>`.
The current version is accepted when enabling a disabled book; an already enabled
book requires a higher version (for example `VERSION=0.2.0`). It preserves unrelated
manifest formatting and edits. It does not commit, push, create a PR, build a PDF,
or create a tag. Direct preparation on `main` or detached HEAD is rejected.
Review and commit the resulting changes with the textbook work, complete the
applicable checks in [Contributing](CONTRIBUTING.md#validation-by-change-category),
and submit the usual batch PR. Merging the release preparation authorizes automatic
public release; no second approval is required.

For publication artifacts, tags, and failure recovery, see the
[maintainer publication procedures](maintainer-guide.md#release-publication).
