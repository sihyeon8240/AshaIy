# Repository architecture

## Philosophy

This repository publishes multiple independently assembled mathematics textbooks
through shared infrastructure. Each directory under `books/` owns its
mathematical exposition, bibliography, metadata, and assembly order. Styles,
reusable publishing templates, automation, and formal tooling are centralized so
mechanical and formal improvements benefit every book consistently.

Publication independence and formal dependency are separate properties. Do not
merge books or share LaTeX mathematical sections between them. Book structure is
generated from book-local contents manifests. Every PDF remains independently
readable and buildable, while Lean formalizations depend on the pinned Mathlib
revision for foundations deliberately omitted from exposition.

Book-specific Lean modules do not directly import another textbook. Use existing
Mathlib declarations for shared mathematics and keep book-specific wrapper
theorems in their owning namespace. See [Lean formalization](formalization.md).

## Top-level directories

- `books/` contains each textbook's entry point, metadata, frontmatter customizations, chapters, optional appendices, and bibliography.
- `common/` contains shared publishing infrastructure: styles, assets, and reusable templates. It does not contain book-specific mathematical sections.
- `scripts/` contains repository automation for discovering, building, checking, packaging, and maintaining books.
- `docs/` contains the documentation map plus contributor, maintainer, authoring, formalization, and site-operation guidance subordinate to this architecture contract.
- `tests/` contains the Python unit-test suite for repository automation.
- `lean/` is one pinned Lake project containing book-owned formalization namespaces.
- `books/<book>/chapters/<chapter>/proofs.yml` and `books/<book>/appendices/<appendix>/proofs.yml` link labeled LaTeX results to checked Lean proofs.
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

`ashaiy contents generate --scope chapters` renders each complete `book.tex` from
`common/templates/book.tex`, `config/books.yml`, and the book's `chapters.yml`;
nonempty appendices begin with `\appendix` before `\backmatter`, using A, B, ...
chapter numbers and independent section/theorem numbering.

`ashaiy contents generate --scope sections` generates every chapter and appendix `index.tex`, including
`\chapter`, `\section`, and literal `\input` commands.

`ashaiy contents generate` runs both operations; `--book <slug>` limits any form to one
registered book, and `check` validates without writing. `ashaiy generated generate` runs
Lean aggregation, contents generation, and then site generation.

Generated assembly is committed so ordinary LaTeX tools can build directly, but
it must never be edited by hand.

Section source files contain mathematical content and labels only. They do not
declare `\section`, load packages, or determine assembly order. Each logical
section is named `section-name.tex` and occupies one file. `references.bib`
and any substantive book-specific style or frontmatter overrides remain
hand-maintained book-local sources. Appendix source follows the same
section-only rule under `appendices/name/`; its assembly is generated from
the `appendices` list.

Book-local `overrides/cover.tex` and `overrides/preface.tex`
files may replace the corresponding shared presentation templates.
Optional `overrides/style.sty` extends the shared `textbook` package and
is loaded after it. These overrides are version-controlled book sources, not
machine-local files. Create the `overrides/` directory only when a customization
is needed; absent files retain the shared defaults.

### Declarative contents contract

Both contents manifests use `schema_version: 1`. Slugs are nonempty lowercase
hyphenated identifiers; section slugs may also contain internal ASCII apostrophes
such as `wilson's-theorem`. Titles are nonempty, brace-balanced, single-line
LaTeX strings. Lists must be nonempty and ordered. Unknown fields, duplicate
slugs, missing manifests, missing content files, orphan files, and stale generated
assembly are errors.
The section slug `index` is reserved for generated assembly.

The path rules are deterministic: chapter item `N` with slug `name` owns
`chapters/name/`, and appendix item `N` owns `appendices/name/`; section
item `N` with slug `topic` owns `topic.tex`. Reorder through YAML alone; rename
slugs and their corresponding content paths together, then run `ashaiy contents generate`. Do
not add hand-written chapter or section commands to content files.

`scripts/contents_manifest.py` is the reusable loader, validator, path mapper,
and renderer. `scripts/contents_generation.py` coordinates generation, while
`scripts/repository_cli.py` owns contents argument parsing and error handling. `scripts/generate_contents.py`
provides a standalone command-line entry point using the same parser. Source
checks run generation in check mode before structural validation, README checks,
and compilation.

## Shared runtime configuration

```text
config/toolchain.env       -> Docker, CI Python, Lean, and Python tooling consumers
config/container-image.txt -> local and devcontainer image consumers
config/ignore-patterns.yml -> Git, Docker, tree, and VS Code exclusion consumers
config/image-build.json    -> image input detection, tag hashing, build matrix, and index checks
config/authoring.json      -> CLI/editor shell formatting and unittest discovery
config/books.yml           -> VS Code task book choices
.vscode/extensions.json   -> devcontainer extension installation
```

These files are the canonical repository configuration. Run `ashaiy config generate` after
editing them to synchronize format-specific consumers, including
`lean/lean-toolchain`, `lean/lakefile.toml`, `.github/requirements-ci.txt`,
`config/pyproject.toml`, and `.devcontainer/devcontainer.json`. `ashaiy config check`
fails on drift.

Commit synchronized consumers with their canonical sources. In particular:

- `config/image-build.json` owns hashed image inputs, build policy, and platform/
  runner pairs. Image jobs read it at runtime; main CI owns automatic image
  preparation and `build-image.yml` provides manual recovery.
- `config/authoring.json` owns shell formatting and test discovery. Synchronization
  updates the corresponding editor fields, book choices, and container extensions.
- `config/ignore-patterns.yml` owns tool-specific exclusion profiles. Generated
  consumers include Git/Docker exclusions, VS Code search/watch settings, and
  `config/generated/cleanup-{files,prune}.txt`. Cleanup profiles govern deletion
  separately from display and tracking; tracked-artifact checks are independent.
- `config/schemas/` supplies editor validation; Python parsers own full semantics.
- Actionlint's pin and checksum live in `config/toolchain.env`; its installation
  remains CI-only.

`config/generated/` contains committed outputs; edit their canonical sources.

### Configuration consumer boundaries

| Consumer type | Ownership and reason |
|---|---|
| Runtime readers | Shell/Python tools and image jobs read canonical configuration directly when execution can supply the value. |
| Complete generated files | Toolchain pins, CI requirements, exclusion lists, and publication version macros remain committed outputs for tools that consume those file formats directly. |
| Mixed editor/container files | Synchronization owns the image, extension lists, book choices, and configured editor fields; remaining user-maintained settings are preserved. |
| Mixed TOML files | Synchronization owns the Lean dependency revision and Ruff target version; package metadata, Lean options, and lint policy remain hand-maintained. |

Mixed consumers are intentional compatibility boundaries. Do not generate their
entire files or introduce a parallel template merely to remove a field update.
Synchronization validates the complete update set before writing; check mode
detects drift without changing consumers. Rollback handles
ordinary write failures, not abrupt termination or a filesystem-wide transaction.

The shared preface's `common/templates/formalization-versions.tex` is also
synchronized: Lean comes from `config/toolchain.env`, and Mathlib's tag and exact
commit come from `lean/lake-manifest.json`. Commit it with changes to either
source. These are publication pins, independent of locally installed tools.

Image publication and development pinning follow the
[maintainer procedure](maintainer-guide.md#toolchain-image-operations).

## Metadata and automation

```text
config/books.yml
    -> scripts/books.py
    -> build / check / site / release
```

`config/books.yml` owns each book's title, author, version, slug, label
prefix, optional Lean module, status, ordering, and build, check, release, and
site flags. Automation consumes it through `scripts/books.py`, rather than
discovering policy from README or LaTeX prose.

A book with `site: true` must also have `build: true`. Affected-book planning
combines manifest state, Git changes, and TeX dependencies; ambiguous build inputs
safely select all build-enabled books. Site publication selects only site-enabled
PDFs. Workflow files own the implementation details.

Manifest field semantics live in [Site metadata](site-metadata.md#registry-fields).
The root README links to the registry; ignored site pages are generated from it
and proof coverage. See [automation modules](#repository-automation-modules) for
implementation ownership.

## Generated files and local outputs

| Files | Owner and location | Git policy |
|---|---|---|
| Project logo | `common/styles/logo.sty` and `common/templates/artwork.tex`; website export at `site/assets/ashaiy-logo.svg` | Commit sources and synchronized SVG; keep intermediate output under `build/logo/` |
| Complete `books/<slug>/book.tex` and chapter/appendix `index.tex` | Contents generator, from manifests and shared templates | Commit; never edit by hand |
| Lean root and book aggregation modules | Lean generator, from the book registry, contents, and topic manifests | Commit; never edit by hand |
| Synchronized toolchain, image, and exclusion consumers | `ashaiy config generate`, from `config/` | Commit with the canonical configuration |
| `site/books/*.md` | `ashaiy site generate`, from the registry and proof coverage | Ignored; regenerate before local site builds |
| PDFs, LaTeX logs, proof-link probes, verified-build metadata | `build/` | Ignored; never commit |
| LaTeX Workshop output | `vscode-build/` | Ignored; never commit |
| Python, Ruff, LaTeX formatter, and Mathlib download caches | `.cache/{python,ruff,latexindent,mathlib}/` by default | Ignored; never commit |
| Lake dependencies, configuration cache, and build results | `lean/.lake/` | Ignored; never commit |
| Persistent container home | Host `${XDG_CACHE_HOME:-$HOME/.cache}/ashaiy-container/<repository-id>` | Outside the checkout; preserved by cache cleanup |
| Release staging and source-check site rendering | Automatically cleaned temporary directories | Never commit |

Intentionally absent local-only assets remain absent; preserve their fallback
behavior. The `generated-pdfs` publication branch is maintained by CI and owns
its PDF snapshot separately from task branches and `main`.

Snapshot preparation and Git publication have separate owners, described under
[automation modules](#repository-automation-modules). Recovery and deployment
guards are documented in the [maintainer guide](maintainer-guide.md#site-publication-checklist).

## Naming conventions

Python and shell source filenames use `snake_case.py` and `snake_case.sh`.
Public commands such as `ashaiy` and hyphenated CLI options retain their names.

Book filenames and ownership follow [Book assembly](#book-assembly-and-file-responsibilities).
Paths identify subjects and remain stable when entries are reordered. Use
lowercase letters and digits separated by single hyphens for chapter and
appendix directories, beginning with a letter; for example,
`chapters/vector-spaces/`. Each section has one descriptively named
`section-name.tex`.

Chapter and appendix `proofs.yml` files are hand-maintained theorem-to-proof
links. Contents generation initializes missing indexes without replacing entries.
`references.bib` is the book-local bibliography.

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
owns paired mathematical exposition and displayed code.

The Lean project is rooted at `lean/Textbooks.lean`. Topic sources belong to
book-owned chapter or appendix namespaces. Each Lean directory has an ordered
`modules.yml`; contents manifests supply stable namespace names and chapter order.
Topic imports own the dependency graph. Unformalized chapters need no Lean directory.

`ashaiy generated generate` generates book `All.lean` files and `Textbooks.lean`.
`--book` limits book aggregation but always refreshes the complete root.
`generated check` and source checks reject stale aggregation, missing or invalid
topics, and manifests outside registered entries. See the exact
[source layout contract](formalization.md#source-layout).

Chapter and appendix `proofs.yml` files link labeled textbook results to checked
Lean declarations. Verified coverage counts registered results; it does not certify
an entire book or the fidelity of prose and displayed code.

## Stability policy

The directory layout, `config/books.yml` and proof-index schemas, metadata loading,
chapter/index pattern, Lean dependency boundary, build scripts, automation, and
CI are public interfaces. Keep changes compatible and limited to a concrete
maintenance need. Preserve independent book ownership and review interface
changes explicitly.

### Multi-platform toolchain images

`config/toolchain.env` owns tool versions. `ashaiy config generate` derives
`.devcontainer/generated/*.env` for the Python, Lean, binary-tool, and
TeX Live installation steps. These committed inputs isolate Docker cache
invalidation; the independent TeX Live stage is reused across other tool updates.
Register generated image inputs in `config/image-build.json`.

Local containers use `config/container-image.txt`. Main CI prepares and publishes
its image before use; ordinary PRs resolve their published content tag to an
immutable index; image-changing PRs use a tested candidate. See
[image operations](maintainer-guide.md#multi-platform-toolchain-images).

### CI reuse ownership

`build.yml` owns source and affected-book CI. Required checks are **Check sources**
and **Verify textbook builds**; candidate validation is required for image changes.
`scripts/verified_build.py` owns conservative verified-PDF reuse, while
`scripts/github_artifacts.py` owns shared artifact transport and provenance.
Cache hits alone never establish validation. See
[reuse and rebuild procedures](maintainer-guide.md#ci-caches-and-verified-pdf-reuse).

## Repository automation modules

`scripts/ashaiy` is the public command interface; argparse validates subcommands and options.
The main implementation responsibilities are:

| Owner | Responsibility |
|---|---|
| `repository_cli.py` | Contents, generation, book-build, check, and format arguments and diagnostics. |
| `repository_tasks.py`, `task_stages.py` | Ordered execution, invocation-local stage results, and stopping on failure. |
| `book_manifest.py`, `books.py` | Manifest policy and stable CLI presentation; Python checks import the domain module. |
| `book_impact.py`, `source_impact.py`, `ci_changes.py` | PDF dependencies, Lean selection, and shared changed-path discovery. |
| `releases.py` | Release eligibility and semantic-version policy. |
| `impact_plan.py` | Source/PDF selection with independent event and snapshot baselines. Missing comparisons select conservatively. |
| `source_checks.py`, `source_reads.py` | Read-only source checks with an invocation-scoped read snapshot. Writing generation reads preceding stages' output directly. |
| Domain modules such as `contents_generation.py`, `proof_links.py`, and `site_pages.py` | Focused validation and generation behind command-line adapters. |
| `new_book.py` | Scaffold creation, registry updates, and rollback if generation fails. |
| `build_all.py` | Bounded build scheduling, grouped logs, failure aggregation, and process-group cleanup. |
| `check_local_environment.py` | Task-specific and full development-environment diagnostics. |
| `file_updates.py` | Stale-output checks and rollback on ordinary write failures. |
| `snapshot_state.py` | Validating and preparing the complete PDF snapshot before replacement. |
| `publish_snapshot.sh` | Attempt-owned Git worktrees, source metadata, current-main guards, and snapshot publication. |

`repository_commands.py` dispatches maintenance, image/site operations, and book creation/release
preparation to their dedicated tools. Local full checks run sources, formatting,
Lean, then books. CI's source profile runs the selected Lean or links-only check
before deferred repository checks. Stage results are not reused across invocations.

Formatters share `format_code.py` for Python and shell. `format_tex.py` owns
LaTeX formatting, its content cache, and Lean indentation preservation; it delegates
typesetting syntax formatting to `latexindent`. `normalize_eof.py` owns byte-level
newline normalization. Existing shell entry points delegate to these Python modules.
`source_checks.py` also owns required-path, Python compilation, and tracked-artifact
checks; `check_repository.sh` runs Bash syntax checks and ShellCheck before it.
Build entry points share output preparation through `build_support.sh`. Workflow files own execution gates and permissions.
