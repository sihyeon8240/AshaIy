#!/usr/bin/env python3
"""Parse the public ashaiy interface independently of domain operations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import overload

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OVERVIEW = """Books:
  book list [--format json]
      List registered textbooks, their label prefixes, and enabled operations.
  book build [--book BOOK] [--check] [--strict] [--jobs N]
      Build PDFs; add --check to inspect logs and --strict to reject warnings.
  book new --slug SLUG --title "TITLE"
      Create a textbook directory and register it in config/books.yml.
  book release --book BOOK --version VERSION
      Prepare version and assembly changes for review before publication.

Validation and formatting:
  check {source|manifest|proof-links|docs}
      Run a focused source, registry, proof-index, or documentation check.
  check all [--strict]
      Check sources, formatting, Lean, and PDFs for check-enabled textbooks.
  lean {build|check}
      Build Lean; check also verifies proof indexes and their declarations.
  format {tex|py|sh|all} [--check] [--file PATH]
      Format sources, or report drift with --check. --file selects one file.
  test
      Run the Python test suite separately from check all.

Generated content:
  contents {generate|check} [--book BOOK] [--scope chapters|sections|all]
      Generate LaTeX assembly from manifests, or check it without writing.
  generated {generate|check} [--book BOOK]
      Process Lean aggregation, LaTeX assembly, and enabled site pages together.
  config {generate|check}
      Synchronize shared configuration, or report stale generated settings.

Website:
  site {generate|check} [--book BOOK]
      Generate or validate metadata pages for site-enabled textbooks.
  site {build|serve|test}
      Render a local site, preview it, or run rendered browser tests.
      serve accepts --port PORT (default: 4000); build textbook PDFs first.

Environment and maintenance:
  doctor env [--profile pdf|lean|format|site|full]
      Inspect local tools (default: pdf); full checks the pinned toolchain.
  doctor book [--book BOOK]
      Print advisory textbook diagnostics.
  image build [--image TAG]
      Build a development image (default: ashaiy-toolchain:local).
  image run [--image REF] [--command "COMMAND"]
      Open a container shell or execute a Bash command inside it.
  image pin --digest SHA256
      Pin a tested image during the reviewed image-promotion procedure.
  clean {build|source}
      Remove PDF/editor build output or disposable source artifacts.
  clean cache --scope {lake|mathlib|tex|ruff|py|coverage|hypothesis|all}
      Remove only the selected tool caches.
  report
      Print an informational repository health report.
  tree
      Write the repository listing to build/tree.txt.

Automation:
  plan [--source-base REF] [--pdf-base REF] [--release-book SLUG]
      Explain CI source and PDF selection as JSON.
  ci-source --lean-mode {build|links}
      Run the CI source profile with Lean compilation or proof links only.

Selecting textbooks:
  --book accepts a slug, label prefix (la, ma, ent), or unique slug prefix.
  Without --book, book build selects build-enabled books; --check selects
  check-enabled books. Other commands describe their selection in --help.
  --strict requires --check for book builds; --shell-escape enables TeX
  shell escape explicitly. Relative --file paths use the caller's directory.

Examples:
  ashaiy book build --book la --check --strict
  ashaiy contents generate --book ent
  ashaiy format tex --check --file path/to/section.tex
  ashaiy doctor env --profile lean
  ashaiy test
  ashaiy check all --strict"""

ACTION_HELP = {
    "book": {
        "list": "List registered textbooks, label prefixes, and enabled operations.",
        "build": "Build one textbook or all build-enabled textbooks into build/<slug>/book.pdf.",
        "new": "Create a textbook scaffold and register it in config/books.yml.",
        "release": "Prepare a release version and generated assembly for review; publication follows merge and CI.",
    },
    "contents": {
        "generate": "Generate book.tex and chapter/appendix index.tex from contents manifests.",
        "check": "Compare LaTeX assembly with the manifests without writing files.",
    },
    "generated": {
        "generate": "Generate Lean aggregation, LaTeX assembly, and site pages; site-disabled books skip the site step.",
        "check": "Check Lean aggregation, LaTeX assembly, and enabled site pages without writing files.",
    },
    "config": {
        "generate": "Synchronize editor settings, toolchain configuration, exclusions, and publication version macros.",
        "check": "Report shared configuration that differs from its generated consumers without writing files.",
    },
    "lean": {
        "build": "Check generated Lean aggregation and build the pinned Lean project.",
        "check": "Build Lean and verify proof indexes, textbook links, and declaration coverage.",
    },
    "doctor": {
        "env": "Inspect the tools required for a local workflow, or check the full pinned toolchain.",
        "book": "Print advisory diagnostics for one textbook or all registered textbooks.",
    },
    "site": {
        "generate": "Generate metadata pages for site-enabled books under site/books/.",
        "check": "Validate generated site pages without writing; run site generate first in a clean checkout.",
        "build": "Generate site pages, render Jekyll, and copy existing PDFs into build/site-preview/.",
        "serve": "Build the local website and serve it until interrupted; build textbook PDFs first.",
        "test": "Run rendered website and responsive browser tests; requires Jekyll, Chromium, and Playwright.",
    },
    "image": {
        "build": "Build the development Docker image from this checkout.",
        "run": "Mount this checkout in a container and open zsh, or run a Bash command.",
        "pin": "Synchronize the reviewed container image digest; use after testing the image.",
    },
    "clean": {
        "build": "Remove disposable output under build/ and vscode-build/ while preserving tool caches.",
        "source": "Remove source-tree auxiliary files and editor/patch backups while preserving build output and caches.",
        "cache": "Remove the selected tool caches; lake includes downloaded Lean dependencies and build results.",
    },
}


def contents_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("scope", choices=("chap", "sec", "all"))
    parser.add_argument("--book")
    parser.add_argument("--check", action="store_true")


def run_contents(arguments: argparse.Namespace) -> int:
    from scripts.contents_generation import generate

    try:
        return generate(arguments.scope, book=arguments.book, check=arguments.check)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def contents_main() -> int:
    """Preserve the standalone contents command's grammar and diagnostics."""
    parser = argparse.ArgumentParser(
        description="Generate LaTeX textbook assembly from chapters.yml and sections.yml."
    )
    contents_arguments(parser)
    return run_contents(parser.parse_args())


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def resolve_book(value: str) -> str:
    from scripts.book_manifest import load_manifest

    try:
        books = load_manifest()["books"]
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    exact = [book for book in books if book["slug"] == value]
    matches = exact or [
        book
        for book in books
        if book["label_prefix"] == value or book["slug"].startswith(value)
    ]
    if len(matches) == 1:
        return matches[0]["slug"]
    if not matches:
        raise argparse.ArgumentTypeError(f"unknown book: {value}")
    choices = ", ".join(book["slug"] for book in matches)
    raise argparse.ArgumentTypeError(f"ambiguous book '{value}': {choices}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ashaiy",
        usage="%(prog)s COMMAND [ARGS] [OPTIONS]",
        description="Build, validate, and maintain the AshaIy textbooks.\n\n"
        + OVERVIEW,
        epilog="Use ashaiy COMMAND --help or ashaiy COMMAND ACTION --help for details.\n"
        "See docs/developer-workflow.md for the complete workflow.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="ashaiy (repository CLI)"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
        help=argparse.SUPPRESS,
        prog=parser.prog,
    )

    @overload
    def command(name: str, help: str) -> argparse.ArgumentParser: ...

    @overload
    def command(
        name: str, help: str, actions: tuple[str, ...]
    ) -> dict[str, argparse.ArgumentParser]: ...

    def command(name: str, help: str, actions: tuple[str, ...] = ()):
        group = commands.add_parser(
            name, help=help, description=help[0].upper() + help[1:] + "."
        )
        if not actions:
            group.set_defaults(run=run_task)
            return group
        children = group.add_subparsers(
            dest="action", required=True, title="actions", metavar="ACTION"
        )
        result = {}
        for action in actions:
            description = ACTION_HELP[name][action]
            child = children.add_parser(
                action, help=description, description=description
            )
            child.set_defaults(run=run_task)
            result[action] = child
        return result

    def book_option(
        target, *, required: bool = False, selection: str = "all registered textbooks"
    ):
        help = "registered slug, label prefix (e.g. la), or unique slug prefix"
        if not required:
            help += f"; omit to select {selection}"
        target.add_argument(
            "--book",
            type=resolve_book,
            required=required,
            metavar="BOOK",
            help=help,
        )

    books = command("book", "manage textbooks", ("list", "build", "new", "release"))
    books["list"].add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    build = books["build"]
    book_option(build, selection="build-enabled textbooks (check-enabled with --check)")
    build.add_argument(
        "--check",
        action="store_true",
        help="check logs; bulk builds select check-enabled books",
    )
    build.add_argument(
        "--strict",
        action="store_true",
        help="require --check; treat log warnings as errors",
    )
    build.add_argument(
        "--jobs",
        type=positive_integer,
        metavar="N",
        help="maximum parallel bulk builds; overrides BOOK_BUILD_JOBS (default: at most 4 workers)",
    )
    build.add_argument(
        "--shell-escape",
        action="store_true",
        help="enable TeX shell escape for this build",
    )
    build.set_defaults(run=run_book)
    books["new"].add_argument(
        "--slug", required=True, help="new textbook directory and registry slug"
    )
    books["new"].add_argument(
        "--title", required=True, help="textbook title; quote titles containing spaces"
    )
    book_option(books["release"], required=True)
    books["release"].add_argument(
        "--version", required=True, help="release version to prepare for review"
    )

    for name in ("contents", "generated", "config"):
        actions = command(name, f"generate or check {name}", ("generate", "check"))
        for action, target in actions.items():
            target.set_defaults(check=action == "check")
            if name != "config":
                book_option(target)
            if name == "contents":
                target.add_argument(
                    "--scope",
                    choices=("chapters", "sections", "all"),
                    default="all",
                    help="chapters: book.tex; sections: chapter/appendix indexes; all: both (default)",
                )
                target.set_defaults(run=run_contents_task)
            elif name == "generated":
                target.set_defaults(run=run_generated)

    checks = command("check", "validate repository sources or all books")
    checks.add_argument(
        "scope",
        choices=("all", "source", "manifest", "proof-links", "docs"),
        help="all: source, formatting, Lean, and PDF checks; other scopes run one focused check",
    )
    checks.add_argument(
        "--strict",
        action="store_true",
        help="treat PDF log warnings as errors; valid only with all",
    )
    checks.set_defaults(run=run_checks)

    formatting = command("format", "format source files or check formatting")
    formatting.add_argument(
        "scope",
        choices=("tex", "py", "sh", "all"),
        help="source language; all also normalizes repository text-file endings",
    )
    formatting.add_argument(
        "--check",
        action="store_true",
        help="report formatting drift without modifying files",
    )
    formatting.add_argument(
        "--file",
        type=lambda value: str(Path(value).resolve()),
        metavar="PATH",
        help="format one file relative to the caller; requires a single language scope",
    )
    formatting.set_defaults(run=run_format)

    command("lean", "build or verify Lean", ("build", "check"))
    doctor = command("doctor", "diagnose environment or textbooks", ("env", "book"))
    doctor["env"].add_argument(
        "--profile",
        choices=("pdf", "lean", "format", "site", "full"),
        default="pdf",
        help="tools to inspect (default: pdf; full checks the pinned container)",
    )
    book_option(doctor["book"])
    site = command(
        "site",
        "generate, validate, and preview the website",
        ("generate", "check", "build", "serve", "test"),
    )
    for action in ("generate", "check"):
        book_option(site[action], selection="site-enabled textbooks")
    site["serve"].add_argument(
        "--port",
        type=positive_integer,
        default=4000,
        help="local preview port (default: 4000)",
    )
    image = command("image", "manage development images", ("build", "run", "pin"))
    for action in ("build", "run"):
        image[action].add_argument(
            "--image",
            help="image tag (build default: ashaiy-toolchain:local)"
            if action == "build"
            else "image reference (default: reviewed pin in config/container-image.txt)",
        )
    image["run"].add_argument(
        "--command",
        dest="container_command",
        metavar="COMMAND",
        help="Bash command inside the container; quote it to avoid host-shell expansion",
    )
    image["pin"].add_argument(
        "--digest",
        required=True,
        help="tested image digest: 64 lowercase hexadecimal characters, without sha256:",
    )
    clean = command(
        "clean", "remove build outputs or caches", ("build", "source", "cache")
    )
    clean["cache"].add_argument(
        "--scope",
        required=True,
        choices=(
            "lake",
            "mathlib",
            "tex",
            "ruff",
            "py",
            "coverage",
            "hypothesis",
            "all",
        ),
        help="cache to remove; all selects every supported tool cache",
    )
    tests = command("test", "run the repository test suite")
    tests.add_argument(
        "--coverage", action="store_true", help="measure Python branch coverage"
    )
    command("report", "print a repository report")
    command("tree", "write build/tree.txt")

    plan = commands.add_parser(
        "plan",
        help="explain CI source and PDF checks",
        description="Print source and PDF validation selection as JSON using independent Git baselines.",
    )
    plan.add_argument(
        "--source-base",
        default="",
        metavar="REF",
        help="source-check comparison revision; omission selects conservatively",
    )
    plan.add_argument(
        "--pdf-base",
        default="",
        metavar="REF",
        help="PDF comparison revision; omission selects conservatively",
    )
    plan.add_argument(
        "--release-book",
        action="append",
        default=[],
        metavar="SLUG",
        help="registered release book slug; repeat for multiple books",
    )
    plan.set_defaults(run=run_plan)
    ci_source = commands.add_parser(
        "ci-source",
        help="run paired CI source and proof checks",
        description="Run the selected Lean or proof-links stage, then deferred repository source checks.",
    )
    ci_source.add_argument(
        "--lean-mode",
        choices=("build", "links"),
        required=True,
        help="build: compile Lean and check declarations; links: check proof links only",
    )
    ci_source.set_defaults(run=run_ci_sources)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    values = sys.argv[1:] if argv is None else argv
    if not values:
        parser.print_help()
        return 0
    try:
        arguments = parser.parse_args(values)
        return arguments.run(arguments)
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 127
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


def run_contents_task(arguments: argparse.Namespace) -> int:
    arguments.scope = {"chapters": "chap", "sections": "sec", "all": "all"}[
        arguments.scope
    ]
    return run_contents(arguments)


def run_task(arguments: argparse.Namespace) -> int:
    from scripts.repository_commands import execute

    return execute(arguments)


def run_book(arguments: argparse.Namespace) -> int:
    from scripts.repository_tasks import build_books

    if arguments.strict and not arguments.check:
        print(
            "error: strict requires check for a book build\n"
            "usage: ashaiy book build [--book BOOK] --check --strict",
            file=sys.stderr,
        )
        return 2
    return build_books(
        book=arguments.book,
        check=arguments.check,
        strict=arguments.strict,
        jobs=arguments.jobs,
        shell_escape=arguments.shell_escape,
    )


def run_ci_sources(arguments: argparse.Namespace) -> int:
    from scripts.repository_tasks import check_ci_sources

    return check_ci_sources(compile_lean=arguments.lean_mode == "build").returncode


def run_generated(arguments: argparse.Namespace) -> int:
    from scripts.repository_tasks import generate

    try:
        return generate(book=arguments.book, check=arguments.check).returncode
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def run_checks(arguments: argparse.Namespace) -> int:
    from scripts.repository_tasks import check_repository

    if arguments.strict and arguments.scope != "all":
        print("error: strict is only valid for the full check", file=sys.stderr)
        return 2

    return check_repository(arguments.scope, strict=arguments.strict)


def run_plan(arguments: argparse.Namespace) -> int:
    from scripts.impact_plan import create_plan

    try:
        result = create_plan(
            arguments.source_base,
            arguments.pdf_base,
            release_books=tuple(arguments.release_book),
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


def run_format(arguments: argparse.Namespace) -> int:
    from scripts.repository_tasks import format_sources

    if arguments.file and arguments.scope == "all":
        print(
            "error: --file requires a single format scope: tex, py, or sh",
            file=sys.stderr,
        )
        return 2
    return format_sources(
        arguments.scope, check=arguments.check, file=arguments.file
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
