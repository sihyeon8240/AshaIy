# Developer workflow

Use this guide for everyday commands. [Architecture](ARCHITECTURE.md) owns file
and configuration boundaries; [Contributing](CONTRIBUTING.md#validation-by-change-category)
owns required checks; the [maintainer guide](maintainer-guide.md) owns publication
and recovery.

## Development environment

Follow the [container quick start](../README.md#quick-start) or
[Linux/WSL2 installation](local-development.md). Builds use LuaLaTeX through
`latexmk`. `config/toolchain.env` pins tool versions and
`config/container-image.txt` pins the reviewed development image.

`ashaiy doctor env` checks PDF tools. Add `--profile lean`, `--profile format`,
`--profile site`, or `--profile full` for the corresponding toolchain.

`ashaiy check source` also runs basedpyright over Python scripts and tests,
yamllint over repository YAML, check-jsonschema using the editor's local schema
associations, and djLint over site Liquid templates. Python type checking uses
basic mode in `config/pyproject.toml`; YAML rules in `config/yamllint.yml`
preserve the existing sequence indentation and workflow keys. Template linting
does not enforce HTML formatting. These checks also run in source CI and full
local validation. Install the pinned Python tools with
`python3 -m pip install -r .github/requirements-ci.txt` outside the image.

After editing canonical configuration, run `ashaiy config generate` and
`ashaiy config check`, then commit the synchronized consumers.

## Daily development workflow

```sh
ashaiy doctor env
ashaiy book build --book linear-algebra --check --strict
```

Replace `linear-algebra` with the registered book slug. Before review, run the
checks required by [change category](CONTRIBUTING.md#validation-by-change-category).

### Working branches

Keep local `main` aligned with `origin/main` through fast-forward updates.
Never commit or push directly to `main`. Create `local-work` from synchronized
`main` and accumulate focused, independently revertible commits for one manageable
batch PR. Use separate branches and PRs for large, risky, or independently
deferrable work.

Validate the combined batch; the owner reviews and merges it. After merging,
fast-forward `main` and recreate `local-work`. Confirm all old work was merged
or preserved before removing the branch. Start fresh after a squash merge so
merged history does not enter the next PR.

### Build outputs

CLI output lives in ignored `build/<slug>/`; LaTeX Workshop uses ignored
`vscode-build/`. Both use the shared LuaLaTeX configuration and TeX search paths.
Successful PDFs remain for incremental builds; compiler failure or interruption
removes that build's PDF. Log checks run even for incremental builds.

`--check` checks references, citations, and other supported diagnostics;
`--strict` additionally rejects overfull boxes and requires `--check`.
Shell escape is opt-in through `--shell-escape` or the corresponding Workshop recipe.

### Inspecting change impact

```sh
python3 scripts/repository_cli.py plan \
  --source-base <event-base-sha> \
  --pdf-base <snapshot-source-sha>
```

Use the PR/event base for source checks and the last PDF snapshot's `.source-sha`
for cumulative PDF planning. The command does not fetch the snapshot. Missing or
invalid bases conservatively select checks/builds; an empty valid diff selects
none unless `--release-book <slug>` requests a build-eligible target.

The JSON explains selection and reports `working_tree_dirty`. Diffs cover
committed changes through HEAD, while metadata comes from the checkout; use a
clean tree for a CI-equivalent plan. Planning neither runs checks nor determines
release eligibility. See [automation ownership](ARCHITECTURE.md#repository-automation-modules).

## CLI command interface

Use `ashaiy --help` and subcommand `--help` for options. The container launcher
runs `scripts/ashaiy` from the mounted checkout, so CLI edits need no image rebuild.
On a locally installed host, use `./scripts/ashaiy`; the Docker runner
`./scripts/run_container.sh` needs no host Python dependencies.

Commands work from any checkout subdirectory. `--book` accepts a slug, its
`label_prefix`, or a unique slug prefix; exact slugs take precedence. Unknown or
ambiguous selectors fail before execution. Without `--book`:

| Operation | Selection |
|---|---|
| `book build` | `build: true` books |
| `book build --check` | `check: true` books |
| Contents and Lean aggregation generation | All registered books |
| Site generation | `site: true` books |

`generated generate` runs Lean aggregation, contents, then site generation;
`generated check` checks those outputs without writing. A selected site-disabled
book skips the site step; explicit `site generate --book` requires a site-enabled
book. Generation and full checks stop at the first failed stage; earlier
successful generation stages may already have written files.

Bulk builds accept `--jobs`, overriding `BOOK_BUILD_JOBS`; the default is at most
four workers, bounded by CPU and book counts. Output is grouped by book and all
workers finish before failures are reported.

## Terminal containers

With Docker installed, use `./scripts/run_container.sh` from the host. With the
host CLI dependencies installed, the equivalent commands are:

```sh
./scripts/ashaiy image run
./scripts/ashaiy image run --command 'ashaiy book build --book linear-algebra --check --strict'
./scripts/ashaiy image build
./scripts/ashaiy image run --image ashaiy-toolchain:local --command 'ashaiy test'
```

`image run` uses the reviewed pin by default, mounts the checkout at `/workspace`,
and uses the host UID/GID. It opens zsh or executes `--command` with Bash, returning
its status. Quote the command to prevent host-shell expansion. Host credentials
and the Docker socket are not mounted automatically. Docker must have local
access to the checkout and cache paths.

The persistent container home is
`${XDG_CACHE_HOME:-$HOME/.cache}/ashaiy-container/<repository-id>` on the host.
It preserves Elan settings and downloaded toolchains across runs and cleanup.
`image build` builds the host architecture as `ashaiy-toolchain:local` unless
`--image` selects another tag; it does not change the reviewed pin. Follow the
[image publication procedure](maintainer-guide.md#multi-platform-toolchain-images)
for pin changes.

## VS Code tasks and authoring support

Use **Run Build Task** for a selected book, **Run Test Task** for Python tests,
and **Run Task** for strict builds, Lean, generation, formatting, and inspection.
Tasks run the public CLI with the interpreter selected by **Python: Select Interpreter**,
the same choice used by Test Explorer. For local development, select
`.cache/local-venv/bin/python` after setup. The CLI passes that interpreter and its
executable directory to child commands. LaTeX Workshop's default recipe previews PDFs; choose
its strict recipe or the strict build Task for repository log checks.
Diagnostics with file locations appear in Problems; other output stays in the
terminal. Test Explorer discovers `unittest` cases under `tests/`.
`ashaiy test` buffers test output, showing it only when a test fails; expected
error diagnostics from passing tests stay hidden. Coverage mode uses the same behavior.

Workshop formatting and strict log checks use `scripts/run_python.sh`: explicit
`PYTHON`, an activated virtual environment, the local setup environment, then
`python3`. Local schemas provide manifest completion; Python parsers own semantic validation.
`.vscode/extensions.json` owns extension recommendations. Configuration generation
synchronizes container extensions, book choices, and configured editor fields;
reopen the Dev Container after changing its configuration.

## Cleaning outputs and caches

| Command | Removes |
|---|---|
| `ashaiy clean source` | Disposable source-tree auxiliary files, formatter logs, editor/patch backups, and interrupted manifest-write files |
| `ashaiy clean build` | CLI and VS Code build output |
| `ashaiy clean cache --scope <scope>` | The selected repository-local cache below |

| Scope | Default location |
|---|---|
| `tex` | `.cache/latexindent/` |
| `ruff` | `.cache/ruff/` |
| `py` | `.cache/python/` |
| `mathlib` | `.cache/mathlib/` |
| `lake` | `lean/.lake/` |
| `coverage` | `.cache/coverage/` |
| `hypothesis` | `.hypothesis/` |
| `all` | All seven categories |

Source cleanup includes interrupted LaTeX Workshop temporary sources and reports
traversal or removal failures. It preserves build output and caches. Cache cleanup preserves unknown
`.cache/` directories, override paths, shared user caches, and the persistent
container home. It rejects symlinks at cache roots or their immediate parents.
Avoid cleanup while tools are running.

The CLI and containers set Python and Mathlib cache paths. For direct commands
in a host shell, set these before starting Python or Lake:

```sh
export PYTHONPYCACHEPREFIX="$PWD/.cache/python"
export MATHLIB_CACHE_DIR="$PWD/.cache/mathlib"
```

Explicit overrides are respected; `FORMAT_TEX_CACHE_DIR` and `RUFF_CACHE_DIR`
override formatter defaults. Container runs use container paths.

## Formatting

Python, LaTeX, and shell files format on save with the configured tools.
Python explicit saves also apply safe Ruff fixes and organize imports. Install
versions from `config/toolchain.env` outside the container.

```sh
ashaiy format tex
ashaiy format py --check
ashaiy format sh --file scripts/build_book.sh
ashaiy format all --check
```

Omit `--check` to update files; include it to report drift without writing.
`all` runs TeX, Python, shell, then repository-wide newline normalization and
stops at the first failure. Review formatter diffs before committing.

| Scope | Targets and policy |
|---|---|
| `tex` | Tracked `.tex`/`.sty` files; `latexindent`, `config/latexindent.yaml`, two-space indentation, 88-column prose wrapping |
| `py` | `scripts/` and `tests/`; Ruff policy in `config/pyproject.toml` |
| `sh` | `scripts/*.sh`; shfmt's Bash variant and two-space indentation |

`--file <path>` selects one existing, nonignored source inside the checkout,
including an untracked draft. It requires one language scope and the matching
extension. Relative paths resolve from the caller's directory. Save editor
buffers first; CLI formatting reads disk files. Edit generated assembly through
its manifests and generators.

LaTeX wrapping preserves manual breaks and relative Lean indentation; long code
and unbreakable tokens can exceed the wrapping target. TeX parsing is heuristic,
so inspect the result. Inline `\verb` and verbatim-style environments are preserved.
Lean blocks containing multiline string literals are preserved as a whole;
indentation and blank lines inside a literal are part of its value.
EditorConfig preserves Markdown hard-break spaces.
All targets require exactly one final LF; `format all` applies this to every
nonempty tracked text file, excluding binary and untracked files.

Formatting does not replace source or mathematical checks. Choose the required
checks from the [validation matrix](CONTRIBUTING.md#validation-by-change-category).

## Review

Follow the [contribution requirements](CONTRIBUTING.md#pull-requests) and
[maintainer checklist](maintainer-guide.md#pull-request-checklist). Report affected
books, validation results, unresolved warnings, and unavailable local-only assets.

## Project logo

`common/styles/logo.sty` defines the copyright-page wordmark. After editing it,
regenerate the website's outlined SVG from the repository root:

```sh
mkdir -p build/logo
TEXINPUTS=.:common/styles//: lualatex -interaction=nonstopmode -halt-on-error \
  -output-directory=build/logo common/templates/artwork.tex
dvisvgm --pdf --no-fonts --exact-bbox --output=site/assets/ashaiy-logo.svg \
  build/logo/artwork.pdf
scripts/normalize_eof.sh site/assets/ashaiy-logo.svg
```

Commit the sources and SVG; keep intermediate output under ignored `build/logo/`.
Review the covers and site header.

## CI and publication

### Continuous integration

`build.yml` validates sources, formatting, tests, Lean, affected PDFs, and site
output. Required checks are **Check sources** and **Verify textbook builds**.
Book-local inputs select affected consumers; shared or ambiguous PDF inputs
select all build-enabled books. CI may omit Lean compilation for changes without
Lean impact while retaining source and proof-link checks.

Main prepares and publishes its toolchain before consumers run. Ordinary PRs
resolve a published immutable image; image-changing PRs validate a candidate.
See the maintainer guide for [images](maintainer-guide.md#multi-platform-toolchain-images)
and [verified PDF reuse](maintainer-guide.md#ci-caches-and-verified-pdf-reuse).
Workflows own execution gates and permissions.

### Development PDF snapshots

Successful main builds maintain the `generated-pdfs` snapshot used by Pages.
Manually dispatch **Build textbooks** to bootstrap or rebuild all build-enabled
books. PRs do not publish.

Pages deploys an immutable snapshot with its recorded source commit. Superseded
snapshots are skipped. Main checks can retry deployment of the existing snapshot
without rebuilding PDFs; deploying alone republishes that snapshot. To publish
new source changes, run **Build textbooks** first. See
[publication and recovery](maintainer-guide.md#site-publication-checklist).

### Releases

On `local-work` or another development branch, run:

```sh
ashaiy book release --book mathematical-analysis --version 0.1.0
```

This sets the version, enables `release: true`, and regenerates book assembly,
preserving unrelated manifest edits. It requires `build: true` and rejects main
or detached HEAD. It does not commit, build, push, or tag.

Enabling releases permits the current version; an already enabled book requires
a higher semantic version, such as `--version 0.2.0`. A newly registered book
with `release: true` also requests publication. Ordinary content changes and
version changes with `release: false` do not publish.

Review and commit the preparation with the book changes and run the applicable
checks. Merging authorizes automatic publication after main CI passes, without
a second approval. See [release publication](maintainer-guide.md#release-publication)
for artifacts and failure recovery.
