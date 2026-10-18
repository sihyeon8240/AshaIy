# Documentation map

The root [README](../README.md) is the repository overview and quick start. This
directory separates stable policy from task-oriented instructions so that a
rule has one authoritative home. Keep any necessary explanation of a policy
with that policy.

## Choose a guide

| Document | Primary audience | Role |
|---|---|---|
| [Repository architecture](ARCHITECTURE.md) | All contributors | Authoritative structure, ownership, naming, metadata, and stability contract. |
| [Contributing](CONTRIBUTING.md) | Contributors | Submission requirements, authoritative validation matrix, rights, and commit conventions. |
| [Textbook writing guide](writing-guide.md) | Authors and editors | Supported LaTeX authoring interface and content conventions. |
| [Lean formalization](formalization.md) | Formalization contributors | Trust boundary, proof and naming policy, proof links, and book-owned prerequisite boundaries. |
| [Developer workflow](developer-workflow.md) | Repository developers | Everyday commands, branches, formatting, cleanup, and release preparation. |
| [Local development](local-development.md) | Linux and WSL2 contributors | Host installation, task dependencies, and Docker coexistence. |
| [Maintainer guide](maintainer-guide.md) | Maintainers and reviewers | Review, publication and recovery procedures, CI artifact reuse, and toolchain image operations. |
| [Site metadata](site-metadata.md) | Site maintainers | Registry fields, generated pages, local previews, and site validation. |

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
