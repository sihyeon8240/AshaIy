"""Plan and prepare complete PDF snapshots before publication transport runs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.books.book_manifest import load_manifest


@dataclass(frozen=True)
class SnapshotPlan:
    replace: tuple[str, ...]
    remove: tuple[str, ...]


def plan_snapshot(
    existing: Mapping[str, int],
    updated: Mapping[str, int],
    registered: set[str],
    expected: set[str],
    required_updates: set[str] | None = None,
) -> SnapshotPlan:
    for slug, size in sorted(updated.items()):
        if not size:
            raise ValueError(f"PDF artifact is missing or empty: updated-pdfs/{slug}.pdf")
        if slug not in registered:
            raise ValueError(f"unknown PDF artifact slug: {slug}")

    if required_updates is not None:
        missing = sorted(required_updates - updated.keys())
        unexpected = sorted(updated.keys() - required_updates)
        if missing or unexpected:
            raise ValueError(
                f"PDF artifacts differ from the build plan: missing={missing}, "
                f"unexpected={unexpected}; rerun Build textbooks if artifacts expired"
            )

    for slug in sorted(expected):
        if not updated.get(slug, existing.get(slug, 0)):
            raise ValueError(f"snapshot lacks site PDF {slug}; dispatch Build textbooks once to bootstrap all PDFs")
    return SnapshotPlan(
        tuple(sorted(set(updated) & expected)),
        tuple(sorted((set(existing) | set(updated)) - expected)),
    )


def pdf_files(directory: Path, *, artifacts: bool = False) -> dict[str, Path]:
    files = {}
    for path in sorted(directory.glob("*.pdf")):
        if path.is_file():
            files[path.stem] = path
        elif artifacts:
            raise ValueError(f"PDF artifact is missing or empty: {path}")
    return files


def prepare(snapshot: Path, updated: Path, *, required_updates: set[str] | None = None) -> SnapshotPlan:
    books = load_manifest()["books"]
    existing = pdf_files(snapshot / "pdf")
    updates = pdf_files(updated, artifacts=True)
    plan = plan_snapshot(
        {slug: path.stat().st_size for slug, path in existing.items()},
        {slug: path.stat().st_size for slug, path in updates.items()},
        {book["slug"] for book in books},
        {book["slug"] for book in books if book["site"]},
        required_updates,
    )

    destination = snapshot / "pdf"
    if destination.is_dir() and not plan.replace and not plan.remove:
        return plan

    staging = Path(tempfile.mkdtemp(prefix=".pdf-staging-", dir=snapshot))
    previous = staging / "previous"
    installed = False
    try:
        candidate = staging / "next"
        if destination.exists():
            shutil.copytree(destination, candidate)
        else:
            candidate.mkdir()
        for slug in plan.replace:
            shutil.copyfile(updates[slug], candidate / f"{slug}.pdf")
        for slug in plan.remove:
            (candidate / f"{slug}.pdf").unlink(missing_ok=True)

        if destination.exists():
            os.replace(destination, previous)
        try:
            os.replace(candidate, destination)
        except BaseException:
            # Restore on cancellation as well as ordinary installation failures.
            if previous.exists():
                try:
                    os.replace(previous, destination)
                except OSError as error:
                    raise OSError(f"snapshot restoration failed; previous PDFs retained at {previous}") from error
            raise
        installed = True
    finally:
        # A failed rollback must leave its recovery copy available.
        if installed or not previous.exists():
            shutil.rmtree(staging)
    return plan


def parse_build_plan(value: str) -> set[str]:
    try:
        matrix = json.loads(value)
    except json.JSONDecodeError as error:
        raise argparse.ArgumentTypeError("expected a JSON book build matrix") from error
    if (
        not isinstance(matrix, dict)
        or set(matrix) != {"book"}
        or not isinstance(matrix["book"], list)
        or not all(isinstance(slug, str) and slug for slug in matrix["book"])
        or len(matrix["book"]) != len(set(matrix["book"]))
    ):
        raise argparse.ArgumentTypeError("expected a unique list of book slugs")
    return set(matrix["book"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("updated", type=Path)
    parser.add_argument("--build-plan", type=parse_build_plan)
    args = parser.parse_args()
    try:
        prepare(args.snapshot, args.updated, required_updates=args.build_plan)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
