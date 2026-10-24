"""Own integrated generation and full-validation stage ordering."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path

from scripts.source_reads import reuse_source_reads
from scripts.task_stages import Stage, StageResult, run_stages

ROOT = Path(__file__).resolve().parent.parent


def source_check_stages(
    command: Callable[..., int], *, compile_lean: bool
) -> tuple[Stage, Stage]:
    sources = Stage(
        "repository-sources", lambda: command("check_repository.sh", "--defer-lean")
    )
    proofs = (
        Stage("lean", lambda: command("check_lean.sh"))
        if compile_lean
        else Stage("proof-links", lambda: command("check_proof_links.py"))
    )
    return sources, proofs


def check_ci_sources(*, compile_lean: bool, root: Path = ROOT) -> StageResult:
    def command(script: str, *arguments: str) -> int:
        prefix = [sys.executable] if script.endswith(".py") else []
        status = subprocess.run(
            [*prefix, str(root / "scripts" / script), *arguments], cwd=root, check=False
        ).returncode
        return 128 - status if status < 0 else status

    sources, proofs = source_check_stages(command, compile_lean=compile_lean)
    return run_stages((proofs, sources))


def build_books(
    *,
    book: str | None = None,
    check: bool = False,
    strict: bool = False,
    jobs: int | None = None,
    shell_escape: bool = False,
) -> int:
    environment = os.environ.copy()
    if jobs is not None:
        environment["BOOK_BUILD_JOBS"] = str(jobs)
    if shell_escape:
        environment["SHELL_ESCAPE"] = "1"
    if strict:
        environment["CHECK_LOG_STRICT"] = "1"

    def command(*arguments: str) -> int:
        status = subprocess.run(
            arguments, cwd=ROOT, env=environment, check=False
        ).returncode
        return 128 - status if status < 0 else status

    if not book:
        arguments = ("check",) if check else ()
        return command(str(ROOT / "scripts/build_all.sh"), *arguments)

    status = command(str(ROOT / "scripts/build_book.sh"), book)
    if status or not check:
        return status

    options = ("--strict",) if strict else ()
    return command(
        sys.executable,
        str(ROOT / "scripts/check_log.py"),
        *options,
        str(ROOT / "build" / book / "book.log"),
    )


def generate(*, book: str | None = None, check: bool = False) -> StageResult:
    from scripts import contents_generation, lean_generation, site_pages

    stages = (
        Stage(
            "lean-assembly", lambda: lean_generation.generate(book=book, check=check)
        ),
        Stage(
            "contents",
            lambda: contents_generation.generate("all", book=book, check=check),
        ),
        Stage(
            "site",
            lambda: site_pages.generate(book=book, check=check, skip_disabled=True),
        ),
    )
    # Generation writes sources that later stages may read; only checks may cache.
    with reuse_source_reads() if check else nullcontext():
        return run_stages(stages)


def check_all(*, strict: bool = False, root: Path = ROOT) -> StageResult:
    environment = os.environ.copy()
    if strict:
        environment["CHECK_LOG_STRICT"] = "1"

    def command(script: str, *arguments: str) -> int:
        status = subprocess.run(
            [str(root / "scripts" / script), *arguments],
            cwd=root,
            env=environment,
            check=False,
        ).returncode
        return 128 - status if status < 0 else status

    sources, proofs = source_check_stages(command, compile_lean=True)
    return run_stages(
        (
            sources,
            Stage("python-format", lambda: command("format_python.sh", "--check")),
            Stage("shell-format", lambda: command("format_shell.sh", "--check")),
            Stage("tex-format", lambda: command("format_tex.sh", "--check")),
            Stage(
                "source-newlines",
                lambda: command("normalize_eof.sh", "--check", "--exclude-formatted"),
            ),
            proofs,
            Stage("books", lambda: command("build_all.sh", "check")),
        )
    )


def check_repository(scope: str, *, strict: bool = False) -> int:
    if scope == "all":
        return check_all(strict=strict).returncode

    commands = {
        "source": (str(ROOT / "scripts/check_repository.sh"),),
        "manifest": (sys.executable, str(ROOT / "scripts/books.py"), "validate"),
        "proof-links": (sys.executable, str(ROOT / "scripts/check_proof_links.py")),
        "docs": (sys.executable, str(ROOT / "scripts/check_docs.py")),
    }
    status = subprocess.run(commands[scope], cwd=ROOT, check=False).returncode
    return 128 - status if status < 0 else status


def format_sources(
    scope: str, *, check: bool = False, file: str | None = None
) -> StageResult:
    options = ["--check"] if check else []
    if file:
        options.extend(("--file", file))

    def command(script: str) -> int:
        status = subprocess.run(
            [str(ROOT / "scripts" / script), *options], cwd=ROOT, check=False
        ).returncode
        return 128 - status if status < 0 else status

    scripts = {
        "tex": "format_tex.sh",
        "py": "format_python.sh",
        "sh": "format_shell.sh",
    }
    selected = (
        (*scripts.values(), "normalize_eof.sh") if scope == "all" else (scripts[scope],)
    )
    return run_stages(
        Stage(script, lambda script=script: command(script)) for script in selected
    )
