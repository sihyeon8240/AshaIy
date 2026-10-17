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
LaTeX strings. Lists must be nonempty and ordered. The `split` field is not
supported. Unknown fields, duplicate slugs, missing manifests, missing content
files, orphan files, and stale generated assembly are errors.
The section slug `index` is reserved for generated assembly.

The path rules are deterministic: chapter item `N` with slug `name` owns
`chapters/name/`, and appendix item `N` owns `appendices/name/`; section
item `N` with slug `topic` owns `topic.tex`. Reorder through YAML alone; rename
slugs and their corresponding content paths together, then run `ashaiy contents generate`. Do
not add hand-written chapter or section commands to content files.

`scripts/contents_manifest.py` is the reusable loader, validator, path mapper,
and renderer. `scripts/contents_generation.py` coordinates generation, while
`scripts/repository_cli.py` owns contents argument parsing and error handling. `scripts/generate-contents.py`
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

The same synchronization updates the book input in `.vscode/tasks.json` and
the Dev Container extension list. Other task settings remain hand-maintained.

`config/image-build.json` owns the image input list, build policy version, and
Linux architecture/runner pairs. `scripts/image_policy.py` reads this policy at
runtime for tag hashing in `prepare-image.yml` and for the build matrix and
publication architecture list in `build-toolchain.yml`. These workflows are
hand-maintained consumers rather than synchronized configuration outputs.
`ashaiy config generate` generates only the main image workflow path filters in
`build-image.yml`, because GitHub evaluates event filters before job execution.
The filters include pipeline paths owned by `scripts/ci_changes.py`. Affected-book
detection and immutable-index validation read the configuration directly. The configuration itself is a hashed image
input. PR artifact consumers require AMD64.

`config/authoring.json` owns shell formatter arguments and unittest discovery.
The CLI reads shell arguments directly; `ashaiy config generate` synchronizes VS Code
formatter arguments, shell indentation, and test discovery. The test command reads
the discovery settings directly. Other editor settings remain hand-maintained.
Actionlint's version and download checksum live in `config/toolchain.env`;
`scripts/check-actions.sh` reads them without changing its CI-only installation.

Editor-only manifest schemas live under `config/schemas/`; the Python manifest
parsers own full semantic validation.

Exclusion groups in `config/ignore-patterns.yml` share identical patterns;
the `git`, `docker`, `tree`, `vscode-search`, and `vscode-watcher` profiles
select groups using each tool's path and glob syntax. Run `ashaiy config generate` after
editing them and commit the generated
`.gitignore` and `.devcontainer/Dockerfile.dockerignore`. The CLI tree command
reads its profile directly. Git tracking, Docker build context, and tree display have
different purposes, so their profiles intentionally differ. The tracked-artifact
check in `scripts/check-repository.sh` independently enforces source hygiene;
it is not a consumer of these exclusion profiles.

The exclusion generator updates `search.exclude` and `files.watcherExclude`
in `.vscode/settings.json`; authoring settings are synchronized separately as
described above. All remaining editor settings stay hand-maintained.
Commit that file with changes to the VS Code profiles.

The `cleanup-files` profile reuses the LaTeX and temporary-file groups;
`cleanup-prune` lists repository-relative directories excluded from source
cleanup. `ashaiy config generate` generates `config/generated/cleanup-files.txt` and
`config/generated/cleanup-prune.txt` for `scripts/clean-artifacts.sh`. Commit
these lists with their canonical configuration. Cleanup profiles govern deletion and remain
separate from Git, Docker, tree, and editor exclusions.

`config/generated/` contains committed configuration consumers produced by
`ashaiy config generate`; edit their canonical source files in `config/` instead.

### Configuration consumer boundaries

| Consumer type | Ownership and reason |
|---|---|
| Runtime readers | Shell/Python tools and image jobs read canonical configuration directly when execution can supply the value. |
| Complete generated files | Toolchain pins, CI requirements, exclusion lists, and publication version macros remain committed outputs for tools that consume those file formats directly. |
| Mixed editor/container files | Synchronization owns the image, extension lists, book choices, and configured editor fields; remaining user-maintained settings are preserved. |
| Mixed TOML files | Synchronization owns the Lean dependency revision and Ruff target version; package metadata, Lean options, and lint policy remain hand-maintained. |
| Workflow trigger filters | Synchronization owns image workflow paths because event filtering happens before runtime configuration can be read. Other workflow logic remains hand-maintained. |

Mixed consumers are intentional compatibility boundaries. Do not generate their
entire files or introduce a parallel template merely to remove a field update.
Synchronization validates the complete update set before writing; check mode
detects drift without changing consumers. Rollback handles
ordinary write failures, not abrupt termination or a filesystem-wide transaction.

Local and devcontainer consumers use the reviewed immutable image in
`config/container-image.txt`. CI resolves the content-addressed tag for its image
inputs to an immutable index. Main prepares and publishes that image before
consumers run; image-changing PRs pass the tested candidate to formatting and PDF
jobs, using a verified run-local archive until publication. Publication and pinning follow
[Toolchain image operations](maintainer-guide.md#toolchain-image-operations).

The shared preface loads `common/templates/formalization-versions.tex`, generated
by `ashaiy config generate`. Lean's version comes from `config/toolchain.env`; Mathlib's
release tag and exact commit come from `lean/lake-manifest.json`, the resolved
dependency lock. Commit this generated TeX file with changes to either source;
`ashaiy config check` detects drift. These publication values describe the pinned
formalization environment, not whichever tools happen to be installed locally.

## Metadata and automation

```text
config/books.yml
    -> scripts/books.py
    -> build / check / site / release
```

`config/books.yml` owns each book's title, author, version, slug, short title, label
prefix, optional Lean module, status, ordering, and build, check, release, and
site flags. Automation consumes it through `scripts/books.py`, rather than
discovering policy from README or LaTeX prose.

A book with `site: true` must also have `build: true`. Affected-book planning
combines manifest state, Git changes, and TeX dependencies; ambiguous build inputs
safely select all build-enabled books. Site publication selects only site-enabled
PDFs. Workflow files own the implementation details.

`scripts/book_impact.py` owns PDF selection and dependency discovery;
`scripts/affected-books.py` adapts that result to the existing CLI formats.
`scripts/source_impact.py` owns conservative Lean selection, while
`scripts/ci_changes.py` owns shared path discovery and consumer classification.
`scripts/impact_plan.py` composes these policies into an inspectable plan with
independent source and PDF baselines and per-consumer/book reasons. The
repository parser's `plan` command presents it as JSON; it does not execute
validation or publication. Release eligibility remains in `scripts/releases.py`.

Reusable manifest policy lives in `scripts/book_manifest.py`: it loads,
normalizes, validates, queries, and safely saves manifest data.
Metadata normalization and checkout file validation are separate operations,
allowing CI to compare manifests from different commits. Release tag validation
uses the same semantic-version policy through `scripts/releases.py`.
`scripts/books.py` is the stable command-line adapter responsible only for
argument parsing, text/JSON presentation, diagnostics, and exit codes. Python
repository checks import the domain module directly; shell automation continues
to use the public CLI.

The root README links to `config/books.yml`. Site book pages are ignored build inputs
generated from that manifest and proof coverage; see [Site metadata](site-metadata.md).

## What belongs where

- Mathematical exposition belongs in the owning book's section files. Never include a section from another textbook.
- Chapter and appendix order and titles belong in `chapters.yml`; section order and titles belong in each entry's `sections.yml`.
- Generated assembly lives in the complete `book.tex` and chapter `index.tex` files; optional presentation overrides belong in the matching `overrides/` files.
- Book-specific preface material, references, and presentation overrides remain in the book directory and are created only when they differ from the shared defaults.
- Book-specific style extensions belong in the owning book's `overrides/style.sty`. Shared mathematics commands, reusable layout structure, repository-wide conventions, templates, and assets belong in `common/`.
- Repository lifecycle automation belongs in `scripts/` and is driven by `config/books.yml`.

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

- `book.tex`: fully generated, stable compiler entry point; do not edit it directly.
- `overrides/cover.tex`: optional book-local replacement for the shared title and copyright template.
- `overrides/preface.tex`: optional book-local replacement for the shared preface template.
- `chapters.yml`: canonical ordered chapter slugs and titles plus optional ordered appendices.
- `chapters/<name>/sections.yml`: canonical ordered section slugs and titles.
- `chapters/<name>/index.tex`: generated chapter and section assembly; do not edit.
- Chapter and appendix `proofs.yml`: hand-maintained theorem-to-proof links; contents generation initializes missing files from the empty template without overwriting entries.
- `appendices/<name>/sections.yml` and `index.tex`: appendix counterparts, generated after `\appendix` and before `\backmatter`.
- `section-name.tex`: the single source file for one logical section.
- `references.bib`: predictable book-local bibliography.
- `overrides/style.sty`: optional book-local extensions to the shared mathematics package; omit it when unused.

Manifests are the authority on inclusion and order. Paths identify subjects and
remain stable when entries are reordered. Each section slug identifies exactly
one source file; there are no alphabetic part suffixes. The generator includes
section files in manifest order. Context-dependent names such as
`section-part-2`, `part-3`, `continuation`, and `misc` are prohibited.

Chapter and appendix directory names consist of lowercase letters and digits
separated by single hyphens, beginning with a letter; for example,
`chapters/vector-spaces/index.tex`.

### Labels

Labels are repository-global. Use the owning book's `label_prefix` from
`config/books.yml`; do not infer it from the subject name. Preserve this convention for
chapters, sections, equations, theorems, and other labeled objects: it prevents
collisions in repository-wide checks and makes diagnostics unambiguous. The
descriptive component is hyphen-separated and may contain ASCII uppercase and
lowercase letters and digits; capitalization may preserve mathematical
identifiers such as `R`, `Q`, or `N`.

## Formal verification boundary

New or mathematically revised theorems selected for formalization follow the
[Lean-first authoring policy](formalization.md#authoring-policy) and required
[paired exposition format](writing-guide.md#paired-mathematical-exposition-and-lean-code).
Those guides own authoring order, displayed-source correspondence, prerequisite
boundaries, and human review obligations.

`ashaiy check all` validates publication sources and the pinned Lean project.
Chapter-owned `books/<book>/chapters/<chapter>/proofs.yml` and appendix-owned
`books/<book>/appendices/<appendix>/proofs.yml` shards own theorem-to-proof links.
The [formalization checks](formalization.md#validation-commands) reject unfinished
proofs and repository-defined axioms and check registered proof types and axiom
dependencies. Verification coverage is the set of registered results, not a claim
about a whole book.

The Lean project is rooted at `lean/Textbooks.lean`. Mathematical sources use
`lean/Textbooks/<Book>/ChapterName/<Topic>.lean` or
`lean/Textbooks/<Book>/Appendices/AppendixName/<Topic>.lean`, with declarations in the matching
`<Book>.ChapterName` or `<Book>.Appendices.AppendixName` namespace. `Textbooks` is a module-path
prefix only. Each existing chapter or appendix directory owns a
`modules.yml` with `schema_version: 1` and an ordered `modules` list of topic
names without extensions. The book's `chapters.yml` supplies chapter and
appendix order; no Lean directory or manifest is required for unformalized
chapters. An existing directory may declare `modules: []` only when it has no
Lean sources.

`ashaiy generated generate` generates book-level `All.lean` files and the root
`Textbooks.lean`; `ashaiy generated check` checks them without writing.
`--book <slug>` limits book aggregation but always includes the complete root
aggregation from `config/books.yml`. Missing, duplicate, invalid, or unregistered
topics and manifests outside registered chapters are errors. Source and Lean
checks also reject stale aggregation. These manifests own reading order and
membership; individual topic imports still own the actual dependency graph.
See [source layout](formalization.md#source-layout) for topic organization and
[dependency policy](formalization.md#dependency-policy) for permitted imports.

## Stability policy

The directory layout, `config/books.yml` and proof-index schemas, metadata loading,
chapter/index pattern, Lean dependency boundary, build scripts, automation, and
CI are public interfaces. Keep changes compatible and limited to a concrete
maintenance need. Preserve independent book ownership and review interface
changes explicitly.

### Multi-platform toolchain images

The image workflow publishes a tested multi-platform image; ordinary PR CI resolves
the published content tag for its image inputs to an immutable index digest. Main
CI prepares its image before use, including on the first push. Canonical
configuration and synchronized consumer ownership are defined above. Runner, tagging, and retention details live in the
[maintainer guide](maintainer-guide.md#multi-platform-toolchain-images).

### CI reuse ownership

`build.yml` is the entry point for source checks, formatting, tested-image
selection, and affected-book validation on PRs and main. Its main image job waits
for publication through the reusable image pipeline; `build-image.yml` also
supports independent publication and recovery. The required source gate includes
candidate validation when image inputs change, and consumers use that candidate.
Required check names are `Check sources` and `Verify textbook builds`. `scripts/verified-build.py`
owns the verified PDF artifact contract and conservative reuse after merge;
cache restores alone never count as validation. Shared transport and provenance
checks live in
`scripts/github_artifacts.py`; PDF, image, and release modules own their file
contracts. `scripts/ci_changes.py` centralizes path discovery and consumer facts.
All PDF and metadata artifacts
are generated under ignored `build/` directories. The
[maintainer guide](maintainer-guide.md#ci-caches-and-verified-pdf-reuse)
documents cache boundaries, artifact eligibility, expiration, and rebuild paths.

## Repository automation modules

`scripts/ashaiy` is the public command interface; argparse validates subcommands and options.
The main implementation responsibilities are:

| Owner | Responsibility |
|---|---|
| `repository_cli.py` | Contents, generation, book-build, check, and format arguments and diagnostics. |
| `repository_tasks.py`, `task_stages.py` | Ordered execution, invocation-local stage results, and stopping on failure. |
| `impact_plan.py` | Source/PDF selection with independent event and snapshot baselines. Missing comparisons select conservatively. |
| `source_checks.py`, `source_reads.py` | Read-only source checks with an invocation-scoped read snapshot. Writing generation reads preceding stages' output directly. |
| Domain modules such as `contents_generation.py`, `proof_links.py`, and `site_pages.py` | Focused validation and generation behind command-line adapters. |
| `file_updates.py` | Stale-output checks and rollback on ordinary write failures. |
| `snapshot_state.py` | Validating and preparing the complete PDF snapshot before replacement. |
| `publish-snapshot.sh` | Attempt-owned Git worktrees, source metadata, current-main guards, and snapshot publication. |

`repository_commands.py` dispatches maintenance, image/site operations, and book creation/release
preparation to their dedicated tools. Local full checks run sources, formatting,
Lean, then books. CI's source profile runs the selected Lean or links-only check
before deferred repository checks. Stage results are not reused across invocations.

Formatters share `format-code.py` for Python and shell; LaTeX uses its own cache
and editor helper. Build entry points share output preparation through
`build-support.sh`. Workflow files own execution gates and permissions.
