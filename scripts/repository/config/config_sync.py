#!/usr/bin/env python3
"""Synchronize format-specific consumers from canonical config files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.books.book_manifest import normalize_manifest
from scripts.repository.config.ignore_patterns import rendered_ignore_consumers
from scripts.repository.config.json_config import parse_json, read_json
from scripts.repository.config.repository_config import (
    IMAGE_PATH,
    ROOT,
    image_name,
    load_authoring,
    load_image,
    load_image_build,
    load_toolchain,
)
from scripts.repository.config.validation_patterns import validation_pattern
from scripts.repository.config.validation_sync import rendered_validation_consumers
from scripts.repository.file_updates import changed_files, source_updates, write_updates
from scripts.repository.source_reads import read_text, read_yaml

SHA256 = re.compile(validation_pattern("sha256"))


def replace_once(
    text: str,
    pattern: str,
    replacement: str | Callable[[re.Match[str]], str],
    path: Path,
) -> str:
    updated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(
            f"{path}: expected exactly one synchronized value, found {count}"
        )
    return updated


def formalization_versions(root: Path, lean_version: str) -> str:
    """Render publication versions from the toolchain and resolved Mathlib lock."""
    path = root / "lean/lake-manifest.json"
    manifest = read_json(path)
    packages = [
        package for package in manifest["packages"] if package["name"] == "mathlib"
    ]
    if len(packages) != 1:
        raise ValueError(f"{path}: expected exactly one Mathlib package")
    package = packages[0]
    release, revision = package["inputRev"], package["rev"]
    if not re.fullmatch("v" + validation_pattern("lean_version"), release):
        raise ValueError(f"{path}: expected a Mathlib release tag")
    if not re.fullmatch(validation_pattern("git_commit"), revision):
        raise ValueError(f"{path}: expected a full Mathlib commit hash")
    if not re.fullmatch(validation_pattern("lean_version"), lean_version):
        raise ValueError("expected a Lean release version")
    return (
        "% Generated from config/toolchain.env and lean/lake-manifest.json; do not edit.\n"
        rf"\newcommand{{\TextbookLeanVersion}}{{{lean_version}}}" + "\n"
        rf"\newcommand{{\TextbookMathlibVersion}}{{{release}}}" + "\n"
        rf"\newcommand{{\TextbookMathlibRevision}}{{{revision}}}" + "\n"
        rf"\newcommand{{\TextbookMathlibShortRevision}}{{{revision[:12]}}}" + "\n"
    )


def rendered_toolchain_groups(root: Path, toolchain: dict[str, str]) -> dict[Path, str]:
    groups = {
        "tools": ("ELAN_", "RUFF_", "SHFMT_", "LATEXINDENT_", "SHELLCHECK_", "GH_"),
        "texlive": ("TEXLIVE_",),
        "lean": ("LEAN_",),
        "python": (
            "PYYAML_",
            "PLAYWRIGHT_",
            "HYPOTHESIS_",
            "COVERAGE_",
            "BASEDPYRIGHT_",
            "YAMLLINT_",
            "DJLINT_",
            "CHECK_JSONSCHEMA_",
        ),
    }
    return {
        root / ".devcontainer/generated" / f"{group}.env": (
            "# Generated from config/toolchain.env; do not edit.\n"
            + "".join(
                f"{key}={value}\n"
                for key, value in toolchain.items()
                if key.startswith(prefixes)
            )
        )
        for group, prefixes in groups.items()
    }


def rendered_issue_forms(root: Path, books: list[dict]) -> dict[Path, str]:
    updates = {}
    for name in ("mathematical-error", "typo"):
        path = root / ".github/ISSUE_TEMPLATE" / f"{name}.yml"
        text = read_text(path)
        form = read_yaml(path)
        if not isinstance(form, dict) or not isinstance(form.get("body"), list):
            raise ValueError(f"{path}: expected an issue form body")
        choices = [
            item
            for item in form["body"]
            if isinstance(item, dict) and item.get("id") == "book"
        ]
        if len(choices) != 1 or choices[0]["type"] != "dropdown":
            raise ValueError(f"{path}: expected one textbook dropdown")
        titles = json.dumps([book["title"] for book in books], ensure_ascii=False)
        # Only the options value is generated; preserve the rest of the form.
        updates[path] = replace_once(
            text,
            r"(^      options: )\[[^\n]*\]$",
            lambda match: match[1] + titles,
            path,
        )
    return updates


def rendered_consumers(
    root: Path = ROOT, *, image: str | None = None
) -> dict[Path, str]:
    load_image_build(root)
    toolchain = load_toolchain(root / "config/toolchain.env")
    if image is None:
        image = load_image(root / "config/container-image.txt")
    devcontainer = root / ".devcontainer/devcontainer.json"
    dev_text = read_text(devcontainer)
    parse_json(dev_text)
    dev_text = replace_once(
        dev_text,
        r'("image"\s*:\s*)"[^"]+"',
        rf'\g<1>"{image}"',
        devcontainer,
    )
    dev_data = parse_json(dev_text)
    recommendations = read_json(root / ".vscode/extensions.json")["recommendations"]
    if not isinstance(recommendations, list) or not all(
        isinstance(extension, str) for extension in recommendations
    ):
        raise ValueError("VS Code recommendations must be a list of extension IDs")
    dev_data["customizations"]["vscode"]["extensions"] = recommendations
    dev_text = json.dumps(dev_data, indent=2) + "\n"

    tasks_path = root / ".vscode/tasks.json"
    tasks = read_json(tasks_path)
    book_inputs = [item for item in tasks["inputs"] if item["id"] == "book"]
    if len(book_inputs) != 1:
        raise ValueError(f"{tasks_path}: expected exactly one book input")
    books = normalize_manifest(read_yaml(root / "config/books.yml"))["books"]
    book_inputs[0]["options"] = [book["slug"] for book in books]

    lakefile = root / "lean/lakefile.toml"
    lake_text = replace_once(
        read_text(lakefile),
        r'^(rev\s*=\s*)"v[^"]+"$',
        rf'\g<1>"v{toolchain["LEAN_VERSION"]}"',
        lakefile,
    )
    pyproject = root / "config/pyproject.toml"
    pyproject_text = replace_once(
        read_text(pyproject),
        r'^(target-version\s*=\s*)"py[0-9]+"$',
        rf'\g<1>"py{toolchain["PYTHON_SERIES"].replace(".", "")}"',
        pyproject,
    )
    pyproject_text = replace_once(
        pyproject_text,
        r'^(pythonVersion\s*=\s*)"[0-9.]+"$',
        rf'\g<1>"{toolchain["PYTHON_SERIES"]}"',
        pyproject,
    )
    requirements = (
        f"PyYAML=={toolchain['PYYAML_VERSION']}\nruff=={toolchain['RUFF_VERSION']}\n"
        f"coverage=={toolchain['COVERAGE_VERSION']}\n"
        f"hypothesis=={toolchain['HYPOTHESIS_VERSION']}\n"
        f"playwright=={toolchain['PLAYWRIGHT_VERSION']}\n"
        f"basedpyright=={toolchain['BASEDPYRIGHT_VERSION']}\n"
        f"yamllint=={toolchain['YAMLLINT_VERSION']}\n"
        f"djlint=={toolchain['DJLINT_VERSION']}\n"
        f"check-jsonschema=={toolchain['CHECK_JSONSCHEMA_VERSION']}\n"
    )
    authoring = load_authoring(root)
    ignore_updates = rendered_ignore_consumers(root)
    settings_path = root / ".vscode/settings.json"
    settings = parse_json(ignore_updates[settings_path])
    settings["shfmt.executableArgs"] = authoring["shell_args"]
    settings["[shellscript]"]["editor.tabSize"] = int(authoring["shell_args"][3])
    settings["python.testing.unittestArgs"] = [
        "-v",
        "-t",
        ".",
        "-s",
        authoring["test_directory"],
        "-p",
        authoring["test_pattern"],
    ]
    ignore_updates[settings_path] = json.dumps(settings, indent=2) + "\n"
    return {
        **ignore_updates,
        **rendered_validation_consumers(root),
        **rendered_toolchain_groups(root, toolchain),
        **rendered_issue_forms(root, books),
        root / "common/templates/formalization-versions.tex": formalization_versions(
            root, toolchain["LEAN_VERSION"]
        ),
        devcontainer: dev_text,
        tasks_path: json.dumps(tasks, indent=2) + "\n",
        root / "lean/lean-toolchain": toolchain["LEAN_TOOLCHAIN"] + "\n",
        lakefile: lake_text,
        root / ".github/requirements-ci.txt": requirements,
        pyproject: pyproject_text,
    }


def synchronize(*, root: Path = ROOT, check: bool = False) -> list[Path]:
    with source_updates(root, check=check):
        updates = rendered_consumers(root)
        return changed_files(updates) if check else write_updates(updates)


def set_image_digest(digest: str, root: Path = ROOT) -> list[Path]:
    with source_updates(root):
        return _set_image_digest(digest, root)


def _set_image_digest(digest: str, root: Path) -> list[Path]:
    if not SHA256.fullmatch(digest):
        raise ValueError("digest must be exactly 64 lowercase hexadecimal characters")
    image_path = root / IMAGE_PATH.relative_to(ROOT)
    current = load_image(image_path)
    image = f"{image_name(current)}@sha256:{digest}"
    updates = {image_path: image + "\n", **rendered_consumers(root, image=image)}
    changed = write_updates(updates, durable=True)
    return [image_path, *(path for path in changed if path != image_path)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail on configuration drift"
    )
    parser.add_argument("--set-image-digest", metavar="SHA256")
    args = parser.parse_args()
    try:
        if args.check and args.set_image_digest:
            parser.error("--check and --set-image-digest are mutually exclusive")
        if args.set_image_digest:
            changed = set_image_digest(args.set_image_digest)
        else:
            changed = synchronize(check=args.check)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.check and changed:
        for path in changed:
            print(
                f"error: synchronized configuration is stale: {path}", file=sys.stderr
            )
        return 1
    if changed:
        for path in changed:
            print(f"Updated: {path.relative_to(ROOT)}")
    else:
        print("Repository configuration is synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
