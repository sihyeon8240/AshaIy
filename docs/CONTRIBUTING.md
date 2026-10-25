# Contributing

This guide owns contribution boundaries, required validation, and commit
conventions. Use the [documentation map](README.md) for task instructions.

## Contribution workflow

### Reporting errors

Report typographical or mathematical errors, missing citations, broken references,
and build failures in a GitHub Issue. Include the book and location, current
statement, proposed correction, and mathematical justification where applicable.

Use a Pull Request for a focused correction after checking that an Issue does
not already cover it. Discuss a new chapter, major reorganization, notation
change, or shared-style redesign in an Issue before implementation.

### Development checks

Use the public `ashaiy` interface in the [developer workflow](developer-workflow.md)
and the [validation matrix](#validation-by-change-category) below. Formalized
theorems follow the [Lean-first policy](formalization.md#authoring-policy),
[paired exposition format](writing-guide.md#paired-mathematical-exposition-and-lean-code),
and manual [correspondence review](formalization.md#displayed-code-correspondence).

### Pull requests

Follow the [batch workflow](developer-workflow.md#working-branches) and
[change boundaries](#change-categories). The owner reviews and merges after
required GitHub Actions checks pass. Report affected books/shared files, commands
and results, unavailable checks, unresolved warnings, missing local-only assets,
and source or rights information for new material. Do not commit build output.

## Contribution policies

### Copyright and sources

- Confirm publication rights for new text, proofs, exercises, solutions, and
  figures, including lecture and examination material.
- Cite sources and distinguish mathematical facts from an author's wording.
- Have a human check AI-generated material for correctness, provenance, and
  licensing; do not submit unverified generated results.

### Authoring conventions

Follow the [writing guide](writing-guide.md) for LaTeX and mathematical prose,
and [architecture](ARCHITECTURE.md) for file ownership and generated sources.

#### Blank lines and end-of-file newlines

Use one empty line between semantic blocks and do not add multiple consecutive
empty lines for visual spacing. Language syntax and the configured formatter
take precedence when they require a different number of empty lines, such as
between top-level Python declarations.

Every text source file must end with exactly one line-feed character, with no
additional empty line at the end. Keep blank lines empty; the repository-wide
EditorConfig settings remove trailing whitespace except in Markdown, where
trailing spaces may encode hard line breaks.

## Change classification and validation

### Change categories

Classify changes by their effect, independently of commit type or file extension:

| Category | Typical scope |
|---|---|
| Mathematical content | One textbook's section sources, appendices, bibliography, and mathematically meaningful local notation |
| Typesetting and presentation | Shared styles and templates, book- and site-specific presentation assets, typography, and PDF behavior |
| Formal verification | Lean sources, proof-index entries, and the correspondence between formal declarations and labeled textbook statements |
| Repository engineering | Scripts, tests, CLI commands, configuration, CI, release automation, and site generation |

Use separate commits for unrelated work and formatting-only changes. Use separate
PRs for large, risky, or independently deferrable work. Treat each textbook's
mathematical content independently.

Keep parts of one coherent result together: a theorem's exposition, Lean proof,
and proof-index entry; a manifest edit and generated assembly; or an automation
fix and its regression test. If reverting only one part leaves an incorrect or
meaningless state, they belong together. Validate shared changes against all
affected consumers.

### Validation by change category

This section owns local pre-review validation requirements. Other guides and
templates refer here rather than defining additional blanket requirements.
Run the union of the applicable rows for a change that spans categories.

| Change | Required local validation |
|---|---|
| Documentation only, including book prerequisite policies | `ashaiy check source`; review policy meaning manually |
| Mathematical content or book-local presentation | `ashaiy format tex --check`, `ashaiy check source`, and `ashaiy book build --book <slug> --check --strict` for each affected book |
| Contents manifests, file moves, or generated assembly | Regenerate with `ashaiy contents generate --book <slug>`, then `ashaiy contents check --book <slug>`, `ashaiy check source`, and affected book builds with strict log checks |
| Lean sources or proof-index entries | `ashaiy lean check`, `ashaiy check source`, and affected book builds with strict log checks; apply content formatting checks when TeX changes |
| Python scripts or tests without PDF build effects | `ashaiy format py --check`, `ashaiy test`, and `ashaiy check source` |
| CLI or shell automation without PDF build effects | `ashaiy format sh --check`, `ashaiy test`, and `ashaiy check source` |
| Site generation or presentation without PDF build effects | `ashaiy site generate`, `ashaiy site check`, `ashaiy test`, `ashaiy check source`, and relevant Python/shell formatting checks; preview rendered site changes |
| CI or release automation without PDF build effects | `ashaiy test`, `ashaiy check source`, relevant formatting checks, and `scripts/repository/checks/check_actions.sh` for workflow changes |
| Shared styles/templates, toolchain/dependencies, PDF build infrastructure, or changes with uncertain PDF consumers | Both complete suites: `ashaiy test` and `ashaiy check all --strict`; also `ashaiy config check` for configuration changes |

The complete suites are independent: `ashaiy check all --strict` includes source,
formatting, Lean, and LaTeX checks but does not run Python unit tests. Full checks
build `check: true` books; `ashaiy book build` without `--book` builds `build: true` books,
while `ashaiy book build --check --strict` selects `check: true` books. If a shared change
affects a build-enabled book excluded from full checks, also run its explicit
`ashaiy book build --book <slug> --check --strict` command.

`ashaiy check source` checks structure, generated sources, proof links, Python
types (basedpyright), YAML (yamllint), editor-associated schemas (check-jsonschema),
Liquid templates (djLint), Bash syntax, and ShellCheck at error severity. It runs
neither formatters nor Ruff; run applicable format commands separately.
`ashaiy check docs` is an optional fast preliminary check, already included in
`ashaiy check source`. It checks repository Markdown paths and heading anchors plus the
supported theorem-environment list; it does not validate external URLs or the
truth of prose. Review wording and factual accuracy manually.

Review rendered PDFs when a change can affect fonts, spacing, page breaks,
bookmarks, links, or other visual behavior. Shared styles and common templates
affect every build-enabled book; local frontmatter affects its owning book.
Documentation-only and CI-only changes without PDF effects require no local PDF
build. CI may run broader checks and conservatively build ambiguous consumers.
Explain any unavailable required check rather than claiming an unrun gate passed.

## Commit conventions

Keep commits focused, buildable, and independently revertible under the
[change boundaries](#change-categories). Include required tests and documentation
with their change. Never commit generated PDFs or LaTeX auxiliary files.

Write commit subjects in this form:

    <type>(<scope>): <summary>

Use a lowercase type and scope, no space before the opening parenthesis, and a
lowercase imperative summary without a trailing period. Keep the subject to 72
characters when practical. Use a body when the reason or impact is not clear
from the subject; explain why the change is needed rather than repeating the
diff.

Supported types are:

- `content` for textbook definitions, theorems, proofs, examples, and prose;
- `fix` for defects in source, tooling, or automation;
- `docs` for contributor and repository documentation;
- `refactor` for structural changes that preserve behavior and meaning;
- `style` for formatting-only changes;
- `build` for CLI, LaTeX build, dependency, and packaging configuration;
- `ci` for GitHub Actions and other continuous-integration changes;
- `test` for validation and test code; and
- `chore` for maintenance that does not fit another type.

Use a textbook slug or a stable repository component as the scope, written in
lowercase kebab-case. Use `common` for shared textbook resources and `repo` for
repository-wide changes. Avoid vague summaries such as `update files`, `revise
content`, or `misc fixes`.

Examples:

    content(mathematical-analysis): clarify the definition of uniform continuity
    build(cli): expose textbook commands
    docs(contributing): document textbook validation steps
