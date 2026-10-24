"""Small fixture builders shared by repository tests."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any

import yaml


def book_record(slug: str = "sample", **overrides: object) -> dict[str, Any]:
    return {
        "slug": slug,
        "title": slug.title(),
        "version": "1.0.0",
        "status": "draft",
        "order": 10,
        **overrides,
    }


def manifest_document(
    records: list[dict[str, Any]], **defaults: object
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "defaults": {
            "author": "Author",
            "build": True,
            "check": True,
            "release": False,
            "site": False,
            **defaults,
        },
        "books": records,
    }


def write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_executable(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_CONFIG_COUNT": "4",
            "GIT_CONFIG_KEY_0": "commit.gpgsign",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "tag.gpgsign",
            "GIT_CONFIG_VALUE_1": "false",
            "GIT_CONFIG_KEY_2": "core.hooksPath",
            "GIT_CONFIG_VALUE_2": os.devnull,
            "GIT_CONFIG_KEY_3": "init.defaultBranch",
            "GIT_CONFIG_VALUE_3": "main",
        }
    )
    return environment


def stop_process_group(process: subprocess.Popen[str]) -> None:
    # Callers start a new session so descendants can be stopped on any test exit.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate(timeout=5)


def copy_validation_configuration(root: Path) -> None:
    """Include the runtime dependency in isolated automation checkouts."""
    repository = Path(__file__).resolve().parent.parent
    for relative in (
        "scripts/validation_patterns.py",
        "scripts/__init__.py",
        "scripts/path_policy.py",
        "config/validation-patterns.json",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repository / relative, target)


def copy_script(source: Path, destination: Path) -> None:
    """Copy a script and the Python implementation behind a shell entry point."""
    shutil.copy2(source, destination)
    companions = {
        "normalize_eof.sh": ("normalize_eof.py",),
        "format_tex.sh": (
            "format_tex.py",
            "normalize_eof.py",
            "latex_scan.py",
            "lean_source.py",
        ),
        "format_tex_file.sh": (
            "format_tex.py",
            "normalize_eof.py",
            "latex_scan.py",
            "lean_source.py",
        ),
    }
    directory = destination if destination.is_dir() else destination.parent
    if directory.name == "scripts":
        copy_validation_configuration(directory.parent)
    for name in companions.get(source.name, ()):
        shutil.copy2(source.parent / name, directory / name)
