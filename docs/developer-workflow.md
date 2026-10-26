# Developer workflow

Use this guide for everyday commands. [Architecture](ARCHITECTURE.md) owns file
and configuration boundaries; [Contributing](CONTRIBUTING.md#validation-by-change-category)
owns required checks; the [maintainer guide](maintainer-guide.md) owns publication
and recovery.

## Development environment

Follow the [container quick start](../README.md#quick-start). Development uses
the pinned image through VS Code Dev Containers or the Docker terminal runner.
The host needs Git and Docker. The terminal runner also needs Python 3.10 or newer
and the Dev Container CLI. Builds use LuaLaTeX through `latexmk`.
`config/toolchain.env` pins tool versions and
`config/container-image.txt` pins the reviewed development image.

Inside the container, `ashaiy doctor env` checks the complete pinned toolchain,
repository files, and native executable architectures. It takes no profile options.
See [architecture troubleshooting](#switching-container-architectures) when moving
a checkout between AMD64 and ARM64.

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
python3 scripts/cli/repository_cli.py plan \
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
Run the CLI inside the container. The Docker runner
`./scripts/toolchain/run_container.sh` uses only the host Python standard library
and the Dev Container CLI; repository Python packages stay inside the container.

Commands work from any checkout subdirectory. `--book` accepts a slug, its
`label_prefix`, or a unique slug prefix; exact slugs take precedence. Unknown or
ambiguous selectors fail before execution. Without `--book`:

| Operation | Selection |
|---|---|
| `book build` | `build: true` books |
| `book build --check` | `check: true` books |
| Contents and Lean aggregation generation | All registered books |
| Site generation | `site: true` books |

`generated generate` runs macros, Lean aggregation, contents, then site generation;
`generated check` checks those outputs without writing. `--book` selects a book
but still refreshes shared macros and the Lean root. A site-disabled book skips
the site step; explicit `site generate --book` requires a site-enabled book.
Generation and full checks stop at the first failure; earlier generation stages
may already have written files. See [macro declarations](macros.md#generation-and-formatting)
and [contents assembly](writing-guide.md#contents-manifests-and-metadata) for focused commands.

Bulk builds accept `--jobs`, overriding `BOOK_BUILD_JOBS`; the default is at most
four workers, bounded by CPU and book counts. Output is grouped by book and all
workers finish before failures are reported.
Before building multiple books concurrently, bulk builds initialize Biber's
shared cache once to avoid first-run extraction races. Initialization failures
stop the build before any books start.

## Terminal containers

Run these commands from the host with Docker, Python 3.10 or newer, and the Dev
Container CLI available. Install the CLI with **Dev Containers: Install
devcontainer CLI** in VS Code, or `npm install -g @devcontainers/cli` with a supported
Node.js installation. CLI 0.88.0 is verified; its npm installation requires Node.js
20 or newer. `DEVCONTAINER=/path/to/devcontainer` selects a CLI outside `PATH`.

```sh
./scripts/toolchain/run_container.sh
CMD='ashaiy book build --book linear-algebra --check --strict' \
  ./scripts/toolchain/run_container.sh
./scripts/toolchain/images/build_image.sh
IMAGE=ashaiy-toolchain:local CMD='ashaiy test' \
  ./scripts/toolchain/run_container.sh
```

The runner uses `.devcontainer/devcontainer.json`, including its image, users,
mounts, environment, and lifecycle commands. The image remains synchronized with
`config/container-image.txt`. With the current image, both VS Code and terminal
sessions use root, `/root`, the installed Oh My Zsh theme, and `/usr/local/elan`.
The workspace normally mounts at `/workspaces/<checkout-name>`; consumers use
`ASHAIY_ROOT` rather than assuming `/workspace`. On Linux this also adopts VS Code's
root ownership of newly created files; a future non-root configuration must apply
to both entry points.

Existing VS Code containers for this checkout and configuration are reused,
including stopped containers. New containers run `ashaiy doctor env` before the
shell opens. Exiting a shell leaves the container available to other sessions;
use the printed `docker stop <id>` command when it is unused. Settings that affect
container creation require **Dev Containers: Rebuild Container** after preserving
home changes. Ambiguous containers and stale images fail without deleting data.

Set `CMD` to execute a command with Bash and return its status; quote the value to
prevent host-shell expansion. Preparation logs go to stderr, leaving command
stdout available for pipes. `ashaiy image run --command '...'` provides the same
interface through the public CLI.

`IMAGE` or `ashaiy image run --image <ref>` creates an isolated persistent profile
with the shared configuration and the selected image. The actual image identity
distinguishes rebuilt local tags. Profiles never rewrite the reviewed image pin
or replace the default VS Code container. Their effective configurations and
preparation lock live in the [host cache](ARCHITECTURE.md#generated-files-and-local-outputs).
Docker must have local access to the checkout.

Container homes survive stops and restarts, but rebuilding a container discards
unmounted home changes. The previous terminal home under
`${XDG_CACHE_HOME:-$HOME/.cache}/ashaiy-container/<repository-id>` is retained and
no longer mounted. Copy only needed custom files or additional toolchains after
checking compatibility; copying the entire home would hide the image's shell
configuration again. Cache cleanup preserves this legacy home and runner state.

Host credentials and the Docker socket are not mounted automatically. Check
`git status` and Git author settings in a standalone session. VS Code's credential
helper and forwarded SSH socket can depend on a running editor session; the CLI
does not reproduce those bridges. For independent HTTPS access, authenticate
inside the container with `gh auth login`. SSH agent sharing requires an explicit
mount appropriate to the host; macOS Docker Desktop and Linux use different
socket paths. The host terminal also needs a suitable font to render theme glyphs.

`build_image.sh` builds the host architecture as `ashaiy-toolchain:local` unless
`IMAGE` selects another tag; it does not change the reviewed pin. Follow the
[image publication procedure](maintainer-guide.md#multi-platform-toolchain-images)
for pin changes.

The site preview's container port 4000 is published only on host loopback.
`ashaiy site serve` listens on all container interfaces through the shared
`ASHAIY_SITE_HOST=0.0.0.0` setting; ordinary host execution still defaults to
`127.0.0.1`. `ashaiy site serve --host <address>` overrides the bind address.
The runner prints the actual host preview URL. VS Code's `forwardPorts` remains
available for containers created before port publication was configured.

Choose a host port before creating a container with `ASHAIY_PREVIEW_PORT=4001`.
Use `ASHAIY_PREVIEW_PORT=0` to let Docker allocate a free port, which is useful for
an isolated image profile alongside the default container:

```sh
ASHAIY_PREVIEW_PORT=0 IMAGE=ashaiy-toolchain:local \
  ./scripts/toolchain/run_container.sh
```

Published ports are creation-time settings. Changing the environment variable
does not change an existing default container's bindings; preserve home changes
and rebuild it when needed. A different port selects a separate image profile.

### Switching container architectures

Run `ashaiy doctor env` after moving a checkout between AMD64 and ARM64. It reads
the ELF architecture of Python, the selected Lean toolchain, and cached Lake
executables, and leaves caches unchanged.

Rebuild a reported Lake executable inside `lean/` with
`lake --no-cache build @<package>/<executable>`. For example, dependency tools use
`@batteries/runLinter` and `@importGraph/graph`; for Mathlib's `cache`, run
`lake exe cache --help`. If a stale trace prevents rebuilding, remove only the
reported executable and its adjacent `.trace` file, then retry.

If Elan selected a downloaded toolchain for the previous architecture, reinstall
only the pinned toolchain for the current platform. The terminal container's
container home preserves Elan settings and downloaded toolchains across restarts;
preserve custom installations before recreating the container.

Keep `.cache/mathlib/`: its pinned download format contains Lean artifacts and
generated C sources, which are distinct from locally compiled executables.
Python bytecode and text formatter caches also need no blanket deletion.

## VS Code tasks and authoring support

Use **Run Build Task** for a selected book, **Run Test Task** for Python tests,
and **Run Task** for strict builds, Lean, generation, formatting, and inspection.
Inside the Dev Container, Tasks run the public CLI with the container interpreter
selected by **Python: Select Interpreter**, the same choice used by Test Explorer.
The Dev Container defaults to `/usr/local/bin/python3`.
The CLI passes that interpreter to child commands.
LaTeX Workshop's default recipe previews PDFs; choose
its strict recipe or the strict build Task for repository log checks.
Diagnostics with file locations appear in Problems; other output stays in the
terminal. Test Explorer discovers `unittest` cases under `tests/`.
See the [test guide](../tests/README.md) for focused runs, coverage, and tool-dependent skips.

Workshop formatting and strict log checks use the container's Python.
Repository schemas provide manifest completion. Reopen the Dev
Container after changing its synchronized configuration.

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
Python explicit saves also apply safe Ruff fixes and organize imports. The
container provides the versions pinned in `config/toolchain.env`.
Python and LaTeX editors show an 88-column guide; Markdown wraps to the viewport
without changing source line breaks.

```sh
ashaiy format tex
ashaiy format py --check
ashaiy format sh --file scripts/latex/build_book.sh
ashaiy format all --check
```

Omit `--check` to update files; include it to report drift without writing.
`all` runs TeX, Python, shell, then repository-wide newline normalization and
stops at the first failure. Review formatter diffs before committing.

| Scope | Targets and policy |
|---|---|
| `tex` | Tracked `.tex`/`.sty` files; `latexindent`, `config/latexindent.yaml`, two-space indentation, 88-column prose wrapping |
| `py` | `scripts/` and `tests/`; Ruff also removes redundant parentheses, flags consecutive nested context managers, and formats Python examples in docstrings |
| `sh` | Shell files throughout `scripts/`; shfmt's Bash variant, two-space indentation, indented case clauses, and spaces after redirection operators |

Ruff policy lives in `config/pyproject.toml`; shell options in
`config/authoring.json` synchronize to the editor through `ashaiy config generate`.

`--file <path>` selects one existing, nonignored source inside the checkout,
including an untracked draft. It requires one language scope and the matching
extension. Relative paths resolve from the caller's directory. Save editor
buffers first; CLI formatting reads disk files. Edit generated assembly through
its manifests and generators.

LaTeX formatting preserves manual breaks, relative Lean indentation, and literal
code; long tokens may exceed the wrapping target. TeX parsing is heuristic, so
inspect the result. The [writing guide](writing-guide.md#braces-in-command-arguments-and-scripts)
owns brace normalization and preservation rules; [LaTeX macros](macros.md#generation-and-formatting)
owns manifest signatures and editor behavior. Generate changed macros before formatting.

Every target requires one final LF. `format all` normalizes all nonempty tracked
text files; binary and untracked files are excluded. EditorConfig preserves
Markdown hard-break spaces.

Formatting does not replace source or mathematical checks. Choose the required
checks from the [validation matrix](CONTRIBUTING.md#validation-by-change-category).

## Review

Follow the [contribution requirements](CONTRIBUTING.md#pull-requests) and
[maintainer checklist](maintainer-guide.md#pull-request-checklist).

## Project logo

`common/styles/logo.sty` defines the copyright-page wordmark. After editing it,
regenerate the website's outlined SVG from the repository root:

```sh
mkdir -p build/logo
TEXINPUTS=.:common/styles//: lualatex -interaction=nonstopmode -halt-on-error \
  -output-directory=build/logo common/templates/artwork.tex
dvisvgm --pdf --no-fonts --exact-bbox --output=site/assets/ashaiy-logo.svg \
  build/logo/artwork.pdf
python3 scripts/repository/formatting/normalize_eof.py site/assets/ashaiy-logo.svg
```

Commit the sources and SVG; keep intermediate output under ignored `build/logo/`.
Review the covers and site header.

## CI and publication

### Continuous integration

`build.yml` checks sources, formatting, tests, Lean, affected PDFs, and site output.
Required checks are **Check sources** and **Verify textbook builds**. Shared or
ambiguous PDF inputs select all build-enabled books. Changes without Lean impact
may skip Lean compilation while retaining source and proof-link checks. See
[image operations](maintainer-guide.md#multi-platform-toolchain-images) and
[verified PDF reuse](maintainer-guide.md#ci-caches-and-verified-pdf-reuse) for CI details.

### Development PDF snapshots

Successful main builds maintain the `generated-pdfs` snapshot used by Pages;
PRs do not publish. **Build textbooks** refreshes PDFs; **Deploy static site**
retries the existing snapshot. Follow the
[publication checklist](maintainer-guide.md#site-publication-checklist) for setup and recovery.

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
