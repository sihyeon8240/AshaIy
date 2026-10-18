# Repository instructions for AI agents.

## Repository purpose

This repository contains independently assembled LaTeX mathematics textbooks.
Read [architecture](docs/ARCHITECTURE.md) for file ownership and generated sources,
and [Contributing](docs/CONTRIBUTING.md) for change boundaries, validation, and
commit conventions. `config/books.yml` owns book metadata and automation flags.
CI Python dependency installation and caching must use `.github/requirements-ci.txt`.

## Git workflow

- Follow the [batch workflow](docs/developer-workflow.md#working-branches): keep
  `main` aligned with `origin/main` by fast-forward, and never commit or push to it.
- Accumulate focused, independently revertible commits on `local-work`, created
  from synchronized `main`. Sequential and dependent follow-ups may share a batch;
  use separate task branches when isolation is useful. Split PRs by size, risk,
  and independent deferral, accounting for CI cost and update conflicts.
- Keep a theorem's exposition, Lean proof, and proof-index entry together.
  Separate unrelated maintenance and formatting. Validate the final combined state;
  temporary integration branches are allowed, but avoid history-only merges after
  copying changes.
- After the owner merges, fast-forward `main` and recreate `local-work` only after
  confirming old work was merged or preserved. Do not carry squash-merged history
  into a new batch.
- Follow [commit conventions](docs/CONTRIBUTING.md#commit-conventions).
- Never merge PRs or change branch protection, Actions permissions, or secrets.
- Do not push unless the Codex interface explicitly requires a task PR update.

## Generated and local-only files

- Do not commit generated PDFs or files under `build/`.
- Do not add ignored LaTeX auxiliary files to Git.
- Do not create placeholders for intentionally absent local-only assets.
- Preserve existing fallback logic for missing local-only files unless explicitly asked to change it.

## Editing scope

- Make the smallest change that satisfies the task.
- Preserve document structure, naming conventions, macros, and mathematical notation.
- Do not edit textbook body content unless the task explicitly requires it.
- Do not modify workflows, the devcontainer, or shared styles unless the task explicitly requires it.
- Give each logical section exactly one `section-name.tex` source file;
  do not use alphabetic part suffixes or `split` metadata. Do not edit generated
  assembly or put `\chapter` or `\section` declarations in section sources.
  Run `ashaiy contents generate --book <slug>` after contents-manifest edits. See `docs/ARCHITECTURE.md`.
- If a shared style changes, consider and validate its effect on every textbook.

## Code readability and maintainability

- Follow `.editorconfig` and the existing language formatters: four spaces for
  Python and two spaces by default; honor file-specific
  exceptions. Use `ashaiy format`
  with the appropriate `py`, `sh`, or `tex` scope; do not hand-format against it.
- Separate logical steps with blank lines. Wrap long expressions and commands
  at meaningful boundaries, without splitting literal values or changing output.
  Keep trailing whitespace absent and exactly one final newline.
- Use descriptive names, straightforward conditions, and early returns where
  they reduce nesting. Expand multi-step one-liners. Extract helpers for repeated
  logic or distinct responsibilities, not merely to shorten a function.
- Keep comments concise: explain non-obvious reasons, constraints, or invariants
  near the relevant code. Avoid document-like comment blocks, decorative banners,
  and comments that restate the code. Keep detailed guidance in `docs/`.
- Apply the same readability standards to tests and embedded scripts. Preserve
  intentional malformed fixtures and whitespace-sensitive literals.
- Preserve behavior, diagnostics, and interfaces during readability refactors.
  In TeX, Lean, YAML, shell, and templates, check that whitespace changes do not
  alter parsing, typesetting, quoting, or generated output. Edit generators rather
  than generated files, and keep displayed Lean synchronized with checked sources.
- Review all relevant languages, but leave already clear code alone. Keep
  formatting-only changes separate from structural refactors and run the checks
  required by `docs/CONTRIBUTING.md#validation-by-change-category`.
- Do not add tests merely because new logic was introduced. First consider
  whether it implements a core repository contract or carries a significant
  regression risk. Focus tests on observable behavior of manifest validation,
  generation, build selection, proof correspondence, source preservation, and
  safe publication. Avoid trivial implementation, dispatcher, or configuration
  assertions already covered by broader behavioral tests or existing tools.

## Mathematical exposition

- For new or mathematically revised theorems selected for formalization, pair
  the mathematical statement with its Lean declaration signature and each proof
  reasoning unit with the corresponding Lean code. Follow
  `docs/writing-guide.md#paired-mathematical-exposition-and-lean-code`.
- Check Lean first, keep displayed code synchronized with the checked source,
  and review the mathematical correspondence under `docs/formalization.md`.
  Do not convert unrelated existing content as part of a documentation edit.

## Prerequisite policy documents

- Keep `books/<slug>/formalization.md` concise: accepted mathematical background,
  subjects developed in the book, and significant boundaries or scoped exceptions.
  Group routine facts by topic; name individual results when needed to distinguish
  accepted prerequisites from material the book must prove.
- Preserve mathematical scope when shortening these documents. Broad subject names
  must not silently authorize core results or stronger external theory.
- Link to `docs/formalization.md` for common proof and interface rules. Keep Lean
  API inventories, representation details, and proof recipes beside the relevant
  Lean declarations or in the exposition; use proof indexes for verified coverage.
  Do not grow prerequisite policies into implementation guides or progress reports.

## Lean source organization

- Check `lean/lakefile.toml` and other applicable options before writing Lean;
  do not repeat project defaults in modules.
- Follow [source layout](docs/formalization.md#source-layout) from the first result:
  use book-owned chapter/appendix topic files, never flat chapter files or numbered
  theorem files. Keep `Textbooks` in module paths/imports, not declaration namespaces.
- Set stable `lean_namespace` values in `chapters.yml`; register topic membership
  and order in `modules.yml`, then run `ashaiy generated generate --book <slug>`.
  Do not hand-edit aggregation files; topic imports own dependencies.
- Follow [Lean readability](docs/formalization.md#lean-readability) in checked and
  displayed code: separate reasoning units, indent nested proofs by two spaces,
  wrap long expressions, and keep comments brief. Prose stays outside the
  argument-free `lean` environment.
- Update imports and proof-index entries together with moved or renamed
  declarations, then run `ashaiy lean check`.

## LaTeX validation

Use LuaLaTeX through `latexmk` and the supported CLI. Required checks come from
[the validation matrix](docs/CONTRIBUTING.md#validation-by-change-category):
documentation-only changes use focused checks; shared styles require both
complete suites (`ashaiy test` and `ashaiy check all --strict`).

For an affected textbook, use `ashaiy book build --book <slug> --check --strict`.
Both compiler and log checker must succeed. Report pre-existing warnings rather
than making unrelated changes to silence them.

## Validation cleanup

- Follow `docs/ARCHITECTURE.md#generated-files-and-local-outputs`: commit generated
  assembly and synchronized configuration; keep build output, site pages, and
  tool caches in their designated ignored locations.
- Before finishing, run `git status --short` when Git metadata is available.
- Never stage or commit build artifacts.

## Pull request expectations

Report what changed, affected books/shared files, validation commands and
results, and unresolved warnings or unavailable local-only assets.

The repository owner performs final review and merge. GitHub Actions validate
pull requests and `main`; merged release enablement or version increases for release-enabled books trigger automatic publication
only after main CI validation gates pass. Prepare versions on development branches
with `ashaiy book release --book <slug> --version <version>`; do not create or push
release tags locally.
