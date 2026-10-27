# Repository architecture

## Philosophy

Each directory under `books/` owns an independently readable and buildable
mathematics textbook. Do not merge books or share their LaTeX mathematical
sections. Styles, templates, automation, and the pinned Lean project are shared.
Book-specific Lean modules use Mathlib and their own book's sources under the
[formalization dependency policy](formalization.md#dependency-policy).

This guide owns structure and file boundaries. Use the
[developer workflow](developer-workflow.md) for commands and the
[maintainer guide](maintainer-guide.md) for publication and recovery.

## Top-level directories

- `books/` contains each textbook's entry point, metadata, frontmatter customizations, chapters, optional appendices, and bibliography.
- `common/` contains shared publishing infrastructure: styles, assets, and reusable templates. It does not contain book-specific mathematical sections.
- `scripts/` contains repository automation for discovering, building, checking, packaging, and maintaining books.
- `docs/` contains the [documentation map](README.md) and task-specific guides.
- `tests/` contains the Python unit-test suite for repository automation.
- `lean/` is one pinned Lake project containing book-owned formalization namespaces.
- `site/` contains website source and data.
- `.devcontainer/` defines the supported development container, while `.github/` contains CI, release, issue, and pull-request configuration.
- `build/` contains ignored, disposable CLI output organized by book slug. The editor-only `vscode-build/` directory is also ignored and disposable.

## Book assembly and file responsibilities

```text
config/books.yml
    -> books/<slug>/chapters.yml
        -> chapters/<name>/sections.yml
        -> appendices/<name>/sections.yml
            -> section-name.tex
```

`config/books.yml` registers textbooks and owns repository-level automation policy.
Each book's `chapters.yml` contains the canonical ordered `chapters` list and an
optional ordered `appendices` list; both entries have slugs and LaTeX titles.
Each chapter or appendix `sections.yml` is the canonical ordered list of logical
section slugs and LaTeX titles. Each logical section has exactly one source
file. List position determines printed numbering; paths contain stable slugs
without numeric prefixes. Chapter and appendix entries may specify a stable
`lean_namespace` in UpperCamelCase to connect their Lean sources.

The contents generator renders complete `book.tex` files from
`common/templates/book.tex`, the registry, and `chapters.yml`. It renders chapter
and appendix `index.tex` files from `sections.yml`, including `\chapter`,
`\section`, and literal `\input` commands. Nonempty appendices begin with
`\appendix` before `\backmatter` and use independent A, B, ... numbering.
Commit generated assembly so ordinary LaTeX tools can build directly; never
edit it by hand.

Each section body occupies one `section-name.tex`, containing content and labels
without chapter/section declarations or package loads. The same rule applies
to appendices. `references.bib`, macro manifests, and frontmatter overrides
remain hand-maintained. See the [authoring procedure](writing-guide.md#book-structure-and-manifests).

Book-local `cover.tex` and `preface.tex` may replace the corresponding shared
presentation templates. These are version-controlled book sources, not
machine-local files. The supported TeX search path checks the book directory
before `common/templates/`, so absent local files retain the shared defaults.
Keep optional presentation files beside the book entry point; no override
directory or placeholder files are needed.

Macro manifests and their generated packages live in `styles/`; the book entry
point, contents manifest, prerequisite policy, and bibliography stay at the root.

### Declarative contents contract

Both contents manifests use `schema_version: 1`. Slugs are nonempty lowercase
hyphenated identifiers; section slugs may also contain internal ASCII apostrophes
such as `wilson's-theorem`. Titles are nonempty, brace-balanced, single-line
LaTeX strings. Lists must be nonempty and ordered. Unknown fields, duplicate
slugs, missing manifests, missing content files, orphan files, and stale generated
assembly are errors.
The section slug `index` is reserved for generated assembly.

Chapter slug `name` owns `chapters/name/`, appendix slug `name` owns
`appendices/name/`, and section slug `topic` owns `topic.tex`. Reorder through
YAML alone; rename slugs and their content paths together, then regenerate.
`scripts/books/contents_manifest.py` owns loading, validation, and rendering;
`contents_generation.py` coordinates generation. Source checks reject stale assembly.

## Macro declarations

`common/styles/macros.yml` and optional `books/<slug>/styles/macros.yml` own shared
and book-local mathematical declarations. Their committed `generated-common-macros.sty`
and `generated-book-macros.sty` packages, respectively, and formatter signatures
derive from the same manifests.

`common/styles/textbook.sty` loads mathematical packages and shared generated
macros. Generated `book.tex` conditionally loads its book-local package.
`common/styles/core.sty` owns typography and the display-style math hooks.
The loader, supported declaration kinds, scopes, and validation contract are
documented in [LaTeX macros](macros.md).

## Shared runtime configuration

```text
config/toolchain.env       -> Docker, CI Python, Lean, and Python tooling consumers
config/container-image.txt -> local and devcontainer image consumers
config/ignore-patterns.yml -> Git, Docker, tree, and VS Code exclusion consumers
config/image-build.json    -> image input detection, tag hashing, build matrix, and index checks
config/authoring.json      -> CLI/editor shell formatting and unittest discovery
config/validation-patterns.json -> Python validation and synchronized shell/schema expressions
config/books.yml           -> VS Code task and GitHub issue-form book choices
.vscode/extensions.json   -> devcontainer extension installation
```

These files are the canonical repository configuration. Run `ashaiy config generate` after
editing them to synchronize format-specific consumers, including
`lean/lean-toolchain`, `lean/lakefile.toml`, `.github/requirements-ci.txt`,
`config/pyproject.toml`, and `.devcontainer/devcontainer.json`. `ashaiy config check`
fails on drift.

Commit synchronized consumers, including `config/generated/`, with their sources.
Cleanup profiles govern deletion separately from display and tracking exclusions;
tracked-artifact checks are independent. `config/schemas/` supplies editor
validation; Python parsers own full semantics.

Shared lexical rules belong in `config/validation-patterns.json`. Its loader in
`scripts/repository/config/validation_patterns.py` resolves `${name}` references
and rejects unknown or cyclic references. Python uses unanchored fragments;
schema and shell consumers receive anchored forms. Semantic checks remain with
their callers, including version rules and distinct image-reference grammars.

Configuration synchronization updates schema values marked with
`$comment: "validation-pattern: <name>"` and Bash expressions following
`# validation-pattern: <name>`. Shell conversion accepts only its supported ERE
subset, keeping bootstrap consumers independent of Python. Keep parser,
replacement, diagnostic, and formatter expressions with their owning code;
glob exclusions belong in `config/ignore-patterns.yml`.

### Configuration consumer boundaries

| Consumer type | Ownership and reason |
|---|---|
| Runtime readers | Shell/Python tools and image jobs read canonical configuration directly when execution can supply the value. |
| Complete generated files | Toolchain pins, CI requirements, exclusion lists, and publication version macros remain committed outputs for tools that consume those file formats directly. |
| Mixed editor/container files | Synchronization owns the image, extension lists, book choices, and configured editor fields; remaining user-maintained settings are preserved. |
| Mixed TOML files | Synchronization owns the Lean dependency revision and Ruff target version; package metadata, Lean options, and lint policy remain hand-maintained. |

Preserve hand-maintained fields in mixed consumers; do not replace these files
with complete generated templates. Synchronization validates the full update set
before writing and rolls back ordinary write failures. Abrupt termination is
not transactional; check mode never writes.

The shared preface's `common/templates/formalization-versions.tex` is also
synchronized: Lean comes from `config/toolchain.env`, and Mathlib's tag and exact
commit come from `lean/lake-manifest.json`. Commit it with changes to either
source. These are publication pins, independent of locally installed tools.

Image publication and development pinning follow the
[maintainer procedure](maintainer-guide.md#toolchain-image-operations).

## Metadata and automation

```text
config/books.yml
    -> scripts/books/book_manifest.py
    -> build / check / site / release
```

`config/books.yml` owns book metadata and automation flags. Consumers use
`scripts/books/book_manifest.py`; `books.py` provides the CLI. Do not infer policy
from README or LaTeX prose. Field semantics live in
[Book registry and site](site-metadata.md#registry-fields).

A book with `site: true` must also have `build: true`. Affected-book planning
combines manifest state, Git changes, and TeX dependencies; ambiguous build inputs
safely select all build-enabled books. Site publication selects only site-enabled
PDFs. Workflow files own the implementation details.

Ignored site pages derive from the registry and proof coverage.

## Generated files and local outputs

| Files | Owner and location | Git policy |
|---|---|---|
| Project logo | `common/styles/logo.sty` and `common/templates/artwork.tex`; website export at `site/assets/ashaiy-logo.svg` | Commit sources and synchronized SVG; keep intermediate output under `build/logo/` |
| Complete `books/<slug>/book.tex` and chapter/appendix `index.tex` | Contents generator, from manifests and shared templates | Commit; never edit by hand |
| Lean root and book aggregation modules | Lean generator, from the book registry, contents, and topic manifests | Commit; never edit by hand |
| `common/styles/generated-common-macros.sty` and book-local `styles/generated-book-macros.sty` | `ashaiy macros generate`, from shared and book-local `macros.yml` | Commit with manifests; never edit by hand |
| Synchronized toolchain, image, and exclusion consumers | `ashaiy config generate`, from `config/` | Commit with the canonical configuration |
| `site/_data/books.json` and `site/books/*.html` | `ashaiy site generate`, from the registry and proof coverage; JSON owns projected data and HTML files own routing | Ignored; regenerate before local site builds |
| PDFs, LaTeX logs, proof-link probes, verified-build metadata | `build/` | Ignored; never commit |
| LaTeX Workshop output | `vscode-build/` | Ignored; never commit |
| Python, Ruff, LaTeX formatter, Mathlib, Coverage, and Hypothesis caches | `.cache/{python,ruff,latexindent,mathlib,coverage}/` and `.hypothesis/` by default | Ignored; never commit |
| Lake dependencies, configuration cache, and build results | `lean/.lake/` | Ignored; never commit |
| Development container home | Container writable layer, currently `/root` | Preserved across stops; save unmounted changes before rebuilding |
| Terminal runner profiles and preparation lock | Host `${XDG_CACHE_HOME:-$HOME/.cache}/ashaiy-devcontainers/<repository-id>` | Outside the checkout; preserved by cache cleanup |
| Legacy terminal home | Host `${XDG_CACHE_HOME:-$HOME/.cache}/ashaiy-container/<repository-id>` | Retained for selective migration; no longer mounted automatically |
| Release staging and source-check site rendering | Automatically cleaned temporary directories | Never commit |

Intentionally absent local-only assets remain absent; preserve their fallback
behavior. The `generated-pdfs` publication branch is maintained by CI and owns
its PDF snapshot separately from task branches and `main`.

Snapshot preparation and Git publication remain separate under `scripts/release/`.
See [publication and recovery](maintainer-guide.md#site-publication-checklist).

## Naming conventions

Python and shell source filenames use `snake_case.py` and `snake_case.sh`.
Public commands such as `ashaiy` and hyphenated CLI options retain their names.

Book paths identify subjects and stay stable when reordered. Chapter and
appendix directories begin with a letter and use lowercase letters and digits
separated by single hyphens, such as `chapters/vector-spaces/`. Section names
follow the [contents contract](#declarative-contents-contract).

### Labels

Labels are repository-global. Use the owning book's `label_prefix` from
`config/books.yml`; do not infer it from the subject name. Preserve this convention for
chapters, sections, equations, theorems, and other labeled objects: it prevents
collisions in repository-wide checks and makes diagnostics unambiguous. The
descriptive component is hyphen-separated and may contain ASCII uppercase and
lowercase letters and digits; capitalization may preserve mathematical
identifiers such as `R`, `Q`, or `N`.

## Formal verification boundary

The [formalization guide](formalization.md) owns the Lean-first workflow,
prerequisite boundaries, proof safety, naming, and source layout. The
[writing guide](writing-guide.md#paired-mathematical-exposition-and-lean-code)
owns paired exposition and the placement of displayed code.

`lean/Textbooks.lean` and book `All.lean` entry points are generated from contents
and topic manifests under the [source layout contract](formalization.md#source-layout).
Chapter and appendix `proofs.yml` files are hand-maintained links from labeled
results to Lean declarations. Contents generation initializes missing indexes
without replacing entries. Coverage counts linked results; it does not certify
an entire book or the fidelity of prose and displayed code.

## Stability policy

The directory layout, configuration schemas, metadata loading, chapter/index
pattern, Lean dependency boundary, build scripts, automation, and CI are reviewed
interfaces. Keep consumers, tests, and documentation aligned with their current
contracts. Preserve independent book ownership and review interface changes explicitly.

Repository JSON rejects duplicate keys and nonstandard numeric constants. Editor JSON
schema associations and YAML schema associations also drive CLI validation.

Repository YAML requires unique mapping keys and integer schema versions.
Book, contents, and proof metadata field names must be strings. Anchors
and aliases are accepted; merge keys (`<<`) are rejected. Write fields explicitly
so validation and source-preserving edits share an unambiguous field owner.

### Multi-platform toolchain images

`config/toolchain.env` owns tool versions. `ashaiy config generate` derives
`.devcontainer/generated/*.env` for the Python, Lean, binary-tool, and
TeX Live installation steps. These committed inputs isolate Docker cache
invalidation; the independent TeX Live stage is reused across other tool updates.
Register generated image inputs in `config/image-build.json`.

`config/container-image.txt` owns the local container pin. CI image selection,
publication, and pinning follow [image operations](maintainer-guide.md#multi-platform-toolchain-images).

### CI reuse ownership

`build.yml` owns source and affected-book CI.
`scripts/ci/verified_build.py` owns conservative verified-PDF reuse, while
`scripts/ci/github_artifacts.py` owns shared artifact transport and provenance.
Cache hits alone never establish validation. See
[reuse and rebuild procedures](maintainer-guide.md#ci-caches-and-verified-pdf-reuse).

## Repository automation modules

`scripts/ashaiy` is the public command interface; argparse validates subcommands and options.
Python domain modules use absolute `scripts.*` imports. Entry-point adapters add
the checkout root to the import path when executed directly; internal readers,
caches, and invocation snapshots retain one package identity. Tests import the
same package rather than loading separate module copies.
Automation and tests use matching functional packages:

| Package | Responsibility |
|---|---|
| `cli/` | Public argument parsing, command dispatch, and ordered task execution. |
| `books/` | Book metadata, contents manifests, assembly, scaffolding, and diagnostics. |
| `latex/` | TeX parsing, formatting, PDF builds, and label/log validation. |
| `lean/` | Lean aggregation, source analysis, proof indexes, and declaration audits. |
| `site/` | Site generation, previews, rendered output, and PDF staging. |
| `release/` | Release preparation, packaging, publication, and PDF snapshots. |
| `ci/` | Change impact, build fingerprints, verified reuse, and artifact transport. |
| `toolchain/` | Environment setup, containers, and toolchain image operations. |
| `repository/` | Shared configuration, source checks, code formatting, and cleanup. |

The larger areas use a second level: `repository/checks/`, `repository/config/`,
and `repository/formatting/` separate validation, canonical configuration consumers,
and formatters; `toolchain/images/` owns image policy, preparation, and publication.
Tests mirror these boundaries. Keep smaller functional areas at one level.

Keep entry points with the functionality they invoke. `scripts/ashaiy` and the
image-installed `scripts/ashaiy_launcher.sh` retain stable top-level paths.
Implementation modules expose `main()` when standalone execution is needed;
internal callers invoke these modules directly instead of adding pass-through
Python or shell files. Keep adapters that configure the environment or provide
editor, container, and publication interfaces.

`scripts/cli/repository_tasks.py` owns generation and full-check ordering; stage
results and read snapshots last only for one invocation. Writing generation
reads preceding stages' output directly. `scripts/ci/impact_plan.py` keeps source
and PDF baselines separate, while `scripts/repository/path_policy.py` owns shared
file roles. Unknown PDF inputs and missing comparisons select conservatively.

Snapshot preparation belongs to `scripts/release/snapshot_state.py`; Git worktrees,
current-main guards, and publication belong to `publish_snapshot.sh`. Workflow
files own execution gates and permissions. See [tests](../tests/README.md) for
fixture ownership and discovery, and [formatting](developer-workflow.md#formatting)
for the formatter interface.
