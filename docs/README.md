# Documentation map

Start with the root [README](../README.md) for setup. Each guide below owns one
area; keep rules and their rationale there and link from other guides. Document
stable contracts and actionable steps; leave change history and implementation
walkthroughs in commits and code.

## Choose a guide

| Guide | Owns |
|---|---|
| [Repository architecture](ARCHITECTURE.md) | File ownership, naming, configuration sources, and generated-file boundaries. |
| [Contributing](CONTRIBUTING.md) | Change boundaries, required validation, rights, and commit conventions. |
| [Textbook writing](writing-guide.md) | LaTeX authoring and the presentation of mathematical prose and Lean code. |
| [LaTeX macros](macros.md) | Macro declarations, generated packages, and formatting signatures. |
| [Lean formalization](formalization.md) | Proof safety, prerequisites, Lean layout, proof links, and source correspondence. |
| [Developer workflow](developer-workflow.md) | Daily commands, branches, formatting, cleanup, and release preparation. |
| [Maintainer guide](maintainer-guide.md) | Review, publication, recovery, CI reuse, and image operations. |
| [Book registry and site](site-metadata.md) | Registry field semantics, generated pages, previews, and site validation. |

Each book owns its mathematical prerequisites in `books/<slug>/formalization.md`;
the [Lean formalization guide](formalization.md#book-owned-prerequisite-boundaries)
links the current policies. There is no common mathematical prerequisite baseline.

The [test guide](../tests/README.md) explains focused runs, fixtures, coverage,
and tool-dependent skips. [AGENTS.md](../AGENTS.md) contains automated-agent
instructions. PR and PDF-snapshot README templates live under `.github/`.

When documents appear to disagree, follow [Repository architecture](ARCHITECTURE.md)
for structural policy and `config/books.yml` for current book metadata and automation
flags. Treat `scripts/ashaiy` and `ashaiy --help` as the current public command interface,
then update stale prose rather than preserving a contradiction.
