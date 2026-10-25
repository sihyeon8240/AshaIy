#!/usr/bin/env python3
"""Shared file selection, normalization, and reporting for code formatters."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.repository.config.repository_config import load_authoring


def run(*arguments: str, cwd: Path) -> None:
    subprocess.run(arguments, cwd=cwd, check=True)


def selected_files(root: Path, language: str, file: Path | None = None) -> list[Path]:
    if file is not None:
        path = file.resolve()
        suffix = ".py" if language == "py" else ".sh"
        valid_extension = path.suffix == suffix or (
            language == "py" and path == root / "scripts/ashaiy"
        )
        if not path.is_relative_to(root) or not path.is_file() or not valid_extension:
            raise ValueError(
                f"FILE must be an existing {suffix} file inside the repository"
            )
        relative = path.relative_to(root)
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", "--", str(relative)], cwd=root
        )
        if ignored.returncode != 1:
            raise ValueError("FILE must not be ignored by Git")
        return [relative]

    patterns = (
        ("scripts/ashaiy", "scripts/*.py", "tests/*.py")
        if language == "py"
        else ("scripts/*.sh",)
    )
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            *patterns,
        ],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return [
        Path(name.decode())
        for name in result.stdout.split(b"\0")
        if name and (root / name.decode()).is_file()
    ]


def run_formatter(root: Path, language: str, names: list[str], *, check: bool) -> None:
    if language == "py":
        if check:
            run(
                "ruff",
                "format",
                "--config",
                "config/pyproject.toml",
                "--check",
                "--quiet",
                "--output-format",
                "concise",
                "--color",
                "never",
                *names,
                cwd=root,
            )
            run(
                "ruff",
                "check",
                "--config",
                "config/pyproject.toml",
                "--quiet",
                "--output-format",
                "concise",
                "--color",
                "never",
                *names,
                cwd=root,
            )
        else:
            run(
                "ruff",
                "check",
                "--config",
                "config/pyproject.toml",
                "--fix",
                "--quiet",
                *names,
                cwd=root,
            )
            run(
                "ruff",
                "format",
                "--config",
                "config/pyproject.toml",
                "--quiet",
                *names,
                cwd=root,
            )
    else:
        run(
            "shfmt",
            "-d" if check else "-w",
            *load_authoring(root)["shell_args"],
            *names,
            cwd=root,
        )


def format_sources(
    language: str, *, check: bool = False, file: Path | None = None
) -> int:
    tool = "ruff" if language == "py" else "shfmt"
    if shutil.which(tool) is None:
        print(f"error: {tool} is required", file=sys.stderr)
        return 127

    root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )
    files = selected_files(root, language, file)

    action = "checking" if check else "formatting"
    label = "Python" if language == "py" else "shell"
    print(f"[{language}] {action} {label} source files", flush=True)
    if not files:
        print(f"[{language}] 0 files total: nothing to process")
        return 0

    originals = (
        {path: hashlib.sha256((root / path).read_bytes()).digest() for path in files}
        if not check
        else {}
    )
    # Prefix relative paths so a filename cannot be interpreted as an option.
    names = (
        [f"./{path}" for path in files]
        if file is not None
        else [str(path) for path in files]
    )

    run_formatter(root, language, names, check=check)

    options = ["--check"] if check else []
    run(
        sys.executable,
        str(root / "scripts/repository/formatting/normalize_eof.py"),
        *options,
        *names,
        cwd=root,
    )

    if check:
        print(f"[{language}] {len(files)} files total: all correctly formatted")
        return 0

    changed = [
        path
        for path in files
        if hashlib.sha256((root / path).read_bytes()).digest() != originals[path]
    ]
    for path in changed:
        print(f"[{language}] reformatted: {path}")
    print(
        f"[{language}] {len(files)} files total: {len(changed)} reformatted, "
        f"{len(files) - len(changed)} unchanged"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language", choices=("py", "sh"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()

    try:
        return format_sources(args.language, check=args.check, file=args.file)
    except subprocess.CalledProcessError as error:
        return error.returncode
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
