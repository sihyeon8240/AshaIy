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


REPOSITORY = Path(__file__).resolve().parents[2]


def copy_file(source: Path, destination: Path) -> None:
    """Preserve package paths when copying repository tools into a fixture."""
    if destination.is_dir():
        if destination.name == "scripts" and source.is_relative_to(
            REPOSITORY / "scripts"
        ):
            destination = destination / source.relative_to(REPOSITORY / "scripts")
        else:
            destination = destination / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_validation_configuration(root: Path) -> None:
    """Include runtime configuration and package boundaries in isolated checkouts."""
    for package in (REPOSITORY / "scripts").rglob("__init__.py"):
        copy_file(package, root / package.relative_to(REPOSITORY))
    for relative in (
        "scripts/repository/config/validation_patterns.py",
        "scripts/repository/config/json_config.py",
        "scripts/repository/file_updates.py",
        "scripts/repository/path_policy.py",
        "config/validation-patterns.json",
    ):
        copy_file(REPOSITORY / relative, root / relative)


def copy_script(source: Path, destination: Path) -> None:
    """Copy an entry point and its runtime modules into an isolated checkout."""
    if not source.is_relative_to(REPOSITORY / "scripts"):
        copy_file(source, destination)
        return
    relative = source.relative_to(REPOSITORY)
    fixture_root = destination if destination.is_dir() else destination.parent
    for _ in relative.parts[1:-1]:
        fixture_root = fixture_root.parent
    if fixture_root.name == "scripts":
        fixture_root = fixture_root.parent
    else:
        raise ValueError(f"expected a scripts/ destination: {destination}")
    copy_file(source, fixture_root / relative)
    copy_validation_configuration(fixture_root)
    companions = {
        "format_tex.py": (
            "repository/formatting/normalize_eof.py",
            "latex/latex_scan.py",
            "latex/normalize_braces.py",
            "latex/command_specs.py",
            "latex/macro_manifest.py",
            "latex/macro_generation.py",
            "books/book_manifest.py",
            "repository/source_reads.py",
            "repository/file_updates.py",
            "lean/lean_source.py",
            "latex/format_tex_file.sh",
        ),
        "format_tex_file.sh": (
            "latex/format_tex.py",
            "repository/formatting/normalize_eof.py",
            "latex/latex_scan.py",
            "latex/normalize_braces.py",
            "latex/command_specs.py",
            "latex/macro_manifest.py",
            "latex/macro_generation.py",
            "books/book_manifest.py",
            "repository/source_reads.py",
            "repository/file_updates.py",
            "lean/lean_source.py",
        ),
    }
    for name in companions.get(source.name, ()):
        copy_file(REPOSITORY / "scripts" / name, fixture_root / "scripts" / name)
    if source.name in companions:
        for name in (
            "common/styles/macros.yml",
            "common/styles/generated-common-macros.sty",
        ):
            copy_file(REPOSITORY / name, fixture_root / name)
