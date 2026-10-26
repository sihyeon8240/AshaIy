"""Dispatch repository maintenance operations independently of CLI parsing."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from scripts.repository.config.repository_config import ROOT, load_authoring


def run(script: str, *options: str, environment=None) -> int:
    prefix = [sys.executable] if script.endswith(".py") else []
    result = subprocess.run(
        [*prefix, str(ROOT / "scripts" / script), *options],
        cwd=ROOT,
        env=environment,
        check=False,
    ).returncode
    return 128 - result if result < 0 else result


def book_command(arguments: argparse.Namespace) -> int:
    action = arguments.action
    if action == "list":
        from scripts.books.book_manifest import load_manifest

        books = load_manifest()["books"]
        if arguments.format == "json":
            print(json.dumps(books, indent=2))
        else:
            for book in books:
                flags = ", ".join(
                    name for name in ("build", "check", "release", "site") if book[name]
                )
                print(
                    f"{book['slug']} ({book['label_prefix']})  {book['title']}  [{flags}]"
                )
        return 0
    if action == "new":
        return run("books/new_book.py", arguments.slug, arguments.title)
    return run(
        "release/releases.py",
        "prepare",
        "--book",
        arguments.book,
        "--version",
        arguments.version,
    )


def config_command(arguments: argparse.Namespace) -> int:
    return run(
        "repository/config/config_sync.py", *(["--check"] if arguments.check else [])
    )


def lean_command(arguments: argparse.Namespace) -> int:
    action = arguments.action
    if action == "check":
        return run("lean/check_lean.sh")
    status = run("lean/lean_generation.py", "--check")
    if status:
        return status
    return subprocess.run(["lake", "build"], cwd=ROOT / "lean", check=False).returncode


def doctor_command(arguments: argparse.Namespace) -> int:
    action = arguments.action
    if action == "env":
        return run("toolchain/check_environment.py")
    from scripts.books.book_manifest import load_manifest

    slugs = (
        [arguments.book]
        if arguments.book
        else [book["slug"] for book in load_manifest()["books"]]
    )
    for slug in slugs:
        status = run("books/book_doctor.py", slug)
        if status:
            return status
    return 0


def site_command(arguments: argparse.Namespace) -> int:
    action = arguments.action
    if action in {"generate", "check"}:
        options = ["--book", arguments.book] if arguments.book else []
        if action == "check":
            options.append("--check")
        return run("site/site_pages.py", *options)
    options = ["--port", str(arguments.port)] if action == "serve" else []
    if action == "serve" and arguments.host is not None:
        options.extend(["--host", arguments.host])
    return run("site/site_preview.py", action, *options)


def image_command(arguments: argparse.Namespace) -> int:
    action = arguments.action
    if action == "pin":
        return run(
            "toolchain/images/check_image_reference.py",
            "--set-digest",
            arguments.digest,
        )
    environment = os.environ.copy()
    if arguments.image:
        environment["IMAGE"] = arguments.image
    if action == "run" and arguments.container_command is not None:
        environment["CMD"] = arguments.container_command
    return run(
        "toolchain/images/build_image.sh"
        if action == "build"
        else "toolchain/run_container.sh",
        environment=environment,
    )


def clean_command(arguments: argparse.Namespace) -> int:
    action = arguments.action
    script = {
        "build": "repository/clean.sh",
        "source": "repository/clean_artifacts.sh",
        "cache": "repository/clean_cache.sh",
    }[action]
    return run(script, *([arguments.scope] if action == "cache" else []))


def test_command(arguments: argparse.Namespace) -> int:
    authoring = load_authoring()
    discovery = [
        "discover",
        "-t",
        ".",
        "-s",
        authoring["test_directory"],
        "-p",
        authoring["test_pattern"],
        "-v",
        "--buffer",
    ]
    if not arguments.coverage:
        return subprocess.run(
            [sys.executable, "-m", "unittest", *discovery], cwd=ROOT, check=False
        ).returncode

    environment = {**os.environ, "ASHAIY_TEST_ROOT": str(ROOT)}
    coverage = [
        sys.executable,
        "-m",
        "coverage",
    ]
    config = f"--rcfile={ROOT / 'config/pyproject.toml'}"

    def measure(*options: str) -> int:
        return subprocess.run(
            [*coverage, options[0], config, *options[1:]],
            cwd=ROOT,
            env=environment,
            check=False,
        ).returncode

    status = measure("erase")
    if status:
        return status
    status = measure("run", "-m", "unittest", *discovery)
    combined = measure("combine")
    if combined:
        return status or combined
    reported = measure("report")
    rendered = measure("html")
    return status or reported or rendered


def report_command(arguments: argparse.Namespace) -> int:
    return run("repository/repository_report.py")


def tree_command(arguments: argparse.Namespace) -> int:
    from scripts.repository.config.ignore_patterns import load_patterns

    patterns = load_patterns(ROOT / "config/ignore-patterns.yml")["tree"]
    output = ROOT / "build/tree.txt"
    output.parent.mkdir(exist_ok=True)
    with output.open("w") as stream:
        return subprocess.run(
            ["tree", "--dirsfirst", "-a", "-I", "|".join(patterns)],
            cwd=ROOT,
            stdout=stream,
            check=False,
        ).returncode


def execute(arguments: argparse.Namespace) -> int:
    handlers = {
        "book": book_command,
        "config": config_command,
        "lean": lean_command,
        "doctor": doctor_command,
        "site": site_command,
        "image": image_command,
        "clean": clean_command,
        "test": test_command,
        "report": report_command,
        "tree": tree_command,
    }
    return handlers[arguments.command](arguments)
