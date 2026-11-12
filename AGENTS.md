# Repository instructions for AI agents

This repository contains independently assembled LaTeX mathematics textbooks.
Read [Architecture](docs/ARCHITECTURE.md) for ownership and generated sources,
[Contributing](docs/CONTRIBUTING.md) for change boundaries, validation and commits,
and the [developer workflow](docs/developer-workflow.md) for commands.
`config/books.yml` owns book metadata and automation flags. CI Python installation
and caching must use `.github/requirements-ci.txt`.

## Git and change boundaries

- Fast-forward `main` to `origin/main`; never commit or push to `main`.
- Work on `local-work` created from synchronized `main`. Use separate task
  branches when isolation helps. Keep commits focused and independently
  revertible; separate unrelated maintenance and formatting.
- Keep a theorem's exposition, Lean proof and proof-index entry together.
  Keep manifests and synchronized generated outputs together. Validate the
  combined state and split PRs by size, risk and independent deferral.
- After the owner merges, confirm old work was merged or preserved before
  recreating `local-work`. Do not carry squash-merged history into a new batch
  or make history-only merges after copying changes.
- Never merge PRs or change branch protection, Actions permissions or secrets.
  Do not push unless the Codex interface explicitly requires a task PR update.
- Make the smallest change satisfying the task. Preserve structure, notation,
  macros and public interfaces. Edit textbook bodies, shared styles, workflows
  and the devcontainer only when the task requires those changes.

## Sources and generated files

- Edit generators and canonical configuration, not generated consumers.
  Run the appropriate `ashaiy ... generate` command and commit synchronized
  assembly/configuration with its source.
- Keep one `section-name.tex` per logical section. Do not use alphabetic parts,
  `split` metadata, or chapter/section declarations in section sources.
  After contents edits run `ashaiy contents generate --book <slug>`.
- Never commit PDFs, `build/`, ignored LaTeX auxiliaries or tool caches.
  Do not create placeholders for intentionally absent local-only assets.
  Preserve fallback behavior for missing files.
- Mixed editor/container/TOML consumers retain hand-maintained fields;
  synchronization owns only the fields specified in Architecture.

## Code and mathematical work

Follow the [code readability rules](docs/CONTRIBUTING.md#code-readability) and
configured formatters; use `ashaiy format` for Python, shell and TeX.
Preserve diagnostics, parsing, source bytes, quoting and generated output during
refactors. Leave already clear code alone. Tests should cover observable core
contracts and significant regressions, not repeat dispatchers or configuration.

For new or revised formalized mathematics, check Lean first, then follow
[paired exposition](docs/writing-guide.md#paired-mathematical-exposition-and-lean-code)
and [correspondence review](docs/formalization.md#displayed-code-correspondence).
Do not convert unrelated material during documentation edits.

Book prerequisite policies stay concise: accepted background, core development
and scoped exceptions. Preserve scope; keep API inventories and proof recipes
beside declarations or exposition and coverage in proof indexes. Follow the
[common formalization rules](docs/formalization.md).

Before writing Lean, read `lean/lakefile.toml`; do not repeat project defaults.
Use book-owned chapter/appendix topic files and stable `lean_namespace` values,
register topics in `modules.yml`, then run `ashaiy generated generate --book <slug>`.
Keep `Textbooks` in module paths, not declaration namespaces. Update imports
and proof-index entries with moves/renames, keep displayed code synchronized,
and run `ashaiy lean check`. Follow the guide's source layout and readability
rules from the first result; never add unchecked axioms or unfinished proofs.

## Validation and delivery

Use the [validation matrix](docs/CONTRIBUTING.md#validation-by-change-category).
LuaLaTeX builds go through latexmk and the supported CLI. For an affected book,
`ashaiy book build --book <slug> --check --strict` must pass compilation and log
checks. Shared styles require both complete suites and consideration of every
build-enabled textbook. Report pre-existing warnings instead of unrelated fixes.

Before finishing, run `git status --short`; never stage build artifacts.
Report changes, affected books/shared files, validation and results, unresolved
warnings and unavailable local-only assets. The owner reviews and merges.
Prepare release versions on a development branch with `ashaiy book release`;
never create/push release tags locally. Reviewed release enablement or version
increases publish automatically only after main CI gates pass.
