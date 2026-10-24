# Local development on Linux and WSL2

Linux and WSL2 can run the same checkout CLI and PDF build commands as the
Docker environment. Windows users should run these steps inside their WSL2 Linux
distribution, preferably with the checkout in its Linux filesystem. Native
Windows and macOS are not currently supported local environments.

## Install the base tools

Install Git, Bash, Perl, Python 3.14 or newer with `venv` and pip support, and
TeX Live. Use your distribution's supported installation procedure for Python;
some distribution defaults are older than this repository's Python syntax.
Do not replace the operating system's Python. The container's exact tested
versions are recorded in `config/toolchain.env`.

Install a full TeX Live distribution to cover the textbook packages, fonts,
LuaLaTeX, latexmk, and Biber. Follow the
[official TeX Live installation guide](https://www.tug.org/texlive/quickinstall.html)
and add its platform-specific binary directory to PATH. The repository uses
TeX Gyre Termes. Older TeX installations may produce different results or fail;
use the configured TeX Live year and archive snapshot when matching CI matters.

From the checkout root, create an isolated Python environment:

```sh
PYTHON=python3.14 ./scripts/setup_local.sh
source .cache/local-venv/bin/activate
./scripts/ashaiy doctor env
./scripts/ashaiy book build --book linear-algebra --check --strict
```

Use `PYTHON=python3` instead if that interpreter is already 3.14 or newer.
The setup script installs the pinned Python dependencies from
`.github/requirements-ci.txt` in `.cache/local-venv/`, including the type, YAML,
schema, and template checkers. It does not install system packages or change
shell startup files. Re-running it refreshes these dependencies. Activate it in
each new terminal.
Invoke `./scripts/ashaiy` from the checkout root, or use its absolute path from
another directory. PDFs go to `build/<slug>/book.pdf` in either environment.

## Optional tools and environment checks

`doctor env` checks PDF tools by default. Other profiles are independent:

| Command | Additional installation |
|---|---|
| `./scripts/ashaiy doctor env --profile lean` | elan, then the toolchain in `lean/lean-toolchain`; the project locks Mathlib |
| `./scripts/ashaiy doctor env --profile format` | ripgrep, Ruff, shfmt, ShellCheck, latexindent, basedpyright, yamllint, check-jsonschema, djLint |
| `./scripts/ashaiy doctor env --profile site` | Ruby, Bundler, Jekyll for site builds and previews |
| `./scripts/ashaiy doctor env --profile full` | Complete pinned Debian container toolchain, including browser and PDF inspection utilities |

For formatting, use the versions in `config/toolchain.env`; for example,
install Ruff into the activated environment with
`python -m pip install ruff==<RUFF_VERSION>`. Follow each tool's Linux installation
instructions for the remaining executables. Install elan without selecting an
unrelated default toolchain; run Lean commands from this checkout so the project's
toolchain file takes effect. Initial Lean checks may download toolchains and
Mathlib dependencies.

Profiles check prerequisites, not complete task correctness or PDF equivalence.
Run the checks required by [Contributing](CONTRIBUTING.md#validation-by-change-category).
Site browser tests additionally require Chromium and Playwright; PDF inspection
requires Poppler utilities and Ghostscript. Repository-wide checks also need
ripgrep and ShellCheck. These are not prerequisites for an ordinary PDF build.

## Docker environment

Use the [container quick start](../README.md#quick-start) or
`./scripts/run_container.sh` for the reviewed published image. Build a local image
only when changing it; see [terminal containers](developer-workflow.md#terminal-containers).
Both environments execute the same checkout CLI.

CI and releases use pinned container images as the publishing
reference. Local installations need not match every container utility version,
but changes to TeX packages and fonts can affect layout. Use the container to
resolve environment-dependent differences before submitting a change.
