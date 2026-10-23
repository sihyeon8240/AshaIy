"""Shared changed-path discovery and CI consumer classification."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE_PIPELINE = {
    "scripts/check_image_tag.sh",
    "scripts/ci_changes.py",
    "scripts/image_registry.py",
    ".github/actions/load-toolchain/action.yml",
    ".github/actions/run-toolchain/action.yml",
    "scripts/image_pr.py",
    ".github/workflows/pin-pr-image.yml",
    "scripts/image_policy.py",
    "scripts/repository_config.py",
    "scripts/image_candidate.py",
    "scripts/github_artifacts.py",
    ".github/workflows/build.yml",
    ".github/workflows/build-image.yml",
    ".github/workflows/build-toolchain.yml",
    ".github/workflows/prepare-image.yml",
}
SITE_FILES = {
    "scripts/generate_site_pages.py",
    "scripts/site_pages.py",
    "scripts/lean_coverage.py",
    "scripts/stage_site_pdfs.py",
}
SNAPSHOT_FILES = {
    ".github/generated-pdfs-README.md",
    "scripts/publish_snapshot.sh",
    "scripts/snapshot_state.py",
}
CI_ONLY_FILES = {
    "scripts/image_pr.py",
    "scripts/ci_check_scope.py",
    "scripts/ci_changes.py",
    "scripts/verified_build.py",
    "scripts/github_artifacts.py",
    "scripts/image_candidate.py",
    "scripts/pages_current.sh",
    "scripts/release_package.py",
    "scripts/release_retry.py",
    "scripts/releases.py",
    "scripts/release_plan.sh",
    "scripts/publish_release.sh",
    "scripts/package_book.sh",
    "scripts/check_image_reference.py",
    "scripts/check_image_tag.sh",
    "scripts/config_sync.py",
    "scripts/export_config.sh",
    "scripts/upload_release_assets.sh",
    "scripts/repository_config.py",
    "scripts/snapshot_base.sh",
}


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
    return set(json.loads((root / "config/image-build.json").read_text())["inputs"])


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
