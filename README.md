# AshaIy

This book-oriented monorepo manages mathematics textbooks written in LaTeX as
versioned works in progress. Textbook content and repository code use different
licenses; see [Licensing](#licensing).

Every book can continue to change and expand. A successful build confirms that
the current source compiles, not that its mathematics is complete or free of
errors.

## Books

[`config/books.yml`](config/books.yml) is the canonical textbook registry. Book-local
`chapters.yml` and `sections.yml` files are the canonical contents hierarchy and
generate LaTeX assembly.

## Quick start

Clone the repository and enter it:

```sh
git clone https://github.com/sihyeon8240/AshaIy.git
cd AshaIy
```

With Docker running, open this folder in VS Code with the Dev Containers
extension and select **Dev Containers: Reopen in Container**. Alternatively,
run `./scripts/toolchain/run_container.sh` from a host terminal with Docker,
Python 3.10 or newer, and the Dev Container CLI installed. In VS Code, use
**Dev Containers: Install devcontainer CLI** to install the CLI command.
Inside the container, `ashaiy` runs the CLI from the mounted checkout.
In the container terminal, run:

```sh
ashaiy doctor env
ashaiy book build --book linear-algebra
```

The PDF is written to `build/linear-algebra/book.pdf`. See the
[developer workflow](docs/developer-workflow.md#development-environment) for
toolchain configuration and environment checks.

Development uses the pinned container environment, shared with CI and releases.
The host needs Git and Docker. The terminal runner additionally uses host Python
and the Dev Container CLI; VS Code is optional when the CLI is installed separately.

Use `ashaiy --help` for commands and the
[developer workflow](docs/developer-workflow.md) for builds, formatting, generation,
and releases. Choose required checks by
[change category](docs/CONTRIBUTING.md#validation-by-change-category).

## Repository layout

- `books/<slug>/`: independently assembled textbooks, each entered through `book.tex`
- `common/`: shared LaTeX styles, assets, and book templates
- `config/`: canonical container image and development toolchain versions
- `lean/`: formalizations; chapter and appendix `proofs.yml` files link them to textbook statements
- `scripts/` and `tests/`: repository automation and its tests
- `site/`: website source; generated book pages are ignored
- `docs/`: architecture, contribution, authoring, and maintenance guides

CLI build output belongs under ignored `build/`; LaTeX Workshop uses
ignored `vscode-build/`. See the [repository architecture](docs/ARCHITECTURE.md)
for file ownership, assembly rules, metadata, and generated files.

## Formal verification

Lean kernel-checks selected statements; it does not certify an entire textbook.
Verified LaTeX statements are linked to checked declarations through chapter or
appendix proof-index entries. See the
[Lean formalization guide](docs/formalization.md) for the trust boundary and
workflow.

## Contributing

Report errors with the book and source location. Before submitting changes, read
the [contributing guide](docs/CONTRIBUTING.md); authors should also follow the
[textbook writing guide](docs/writing-guide.md).

## Licensing

Textbook content is licensed under [CC BY 4.0](LICENSE-CC-BY-4.0).
Copyright (c) 2026 Muho Choi. This grant does not relicense third-party material
or establish that every existing passage is original. Third-party names,
trademarks, and material used under separate terms are excluded from this grant.
Their inclusion does not imply ownership or authorization. Contributors must
identify citations and rights for new text, exercises, solutions, and figures.

Repository code and automation are under the [MIT License](LICENSE-MIT),
including `scripts/`, repository-authored build, validation, distribution and release
automation, repository-authored workflow and development-environment
configuration, and `common/styles/`. This does not apply MIT to textbook
content, trademarks, or third-party material. External dependencies remain under
their own licenses.

## Documentation

Use the [documentation map](docs/README.md) to find the guide for your task.
