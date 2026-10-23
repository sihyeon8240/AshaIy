"""Shared changed-path discovery and CI consumer classification."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.path_policy import IMAGE_PIPELINE, SITE_FILES, SNAPSHOT_FILES
from scripts.repository_config import load_image_build

ROOT = Path(__file__).resolve().parent.parent


def changed_paths(
    base: str | None, head: str = "HEAD", *, root: Path | None = None
) -> list[str] | None:
    if not base or set(base) == {"0"}:
        return None
    try:
        output = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "--no-renames",
                "-z",
                "--diff-filter=ACDMRTUXB",
                base,
                head,
                "--",
            ],
            cwd=root,
            check=True,
            text=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None
    return [path for path in output.split("\0") if path]


def image_inputs(root: Path = ROOT) -> set[str]:
    return set(load_image_build(root)["inputs"])


def is_documentation(path: str) -> bool:
    return path.endswith(".md") or path in {
        "LICENSE-MIT",
        "LICENSE-CC-BY-4.0",
    }


def classify(paths: list[str] | None, *, root: Path = ROOT) -> dict[str, bool]:
    return {
        name: selection["selected"]
        for name, selection in consumer_selections(paths, root=root).items()
    }


def consumer_selections(
    paths: list[str] | None, *, root: Path = ROOT
) -> dict[str, dict]:
    names = ("image_changed", "structured", "site_changed", "snapshot_changed")
    if paths is None:
        return {
            name: {
                "selected": True,
                "reason": "comparison unavailable; conservative selection",
                "paths": [],
            }
            for name in names
        }
    inputs = image_inputs(root)
    matches = {
        "image_changed": sorted(set(paths) & (inputs | IMAGE_PIPELINE)),
        "structured": sorted(
            path
            for path in paths
            if (path.startswith(".github/") and path.endswith(".yml"))
            or path
            in {"config/books.yml", "CITATION.cff", ".devcontainer/devcontainer.json"}
        ),
        "site_changed": sorted(
            path
            for path in paths
            if path == "config/books.yml"
            or path in SITE_FILES
            or path
            in {"config/validation-patterns.json", "scripts/validation_patterns.py"}
            or path.startswith("site/")
        ),
        "snapshot_changed": sorted(set(paths) & SNAPSHOT_FILES),
    }
    return {
        name: {
            "selected": bool(matched),
            "reason": "matching consumer inputs"
            if matched
            else "no matching consumer inputs",
            "paths": matched,
        }
        for name, matched in matches.items()
    }
