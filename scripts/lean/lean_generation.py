#!/usr/bin/env python3
"""Generate Lean aggregation modules from the book and topic manifests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.lean.lean_manifest import ROOT, expected_files, stale_files
from scripts.repository.file_updates import source_updates, write_updates


def generate(*, root: Path = ROOT, book: str | None = None, check: bool = False) -> int:
    with source_updates(root, check=check):
        return _generate(root=root, book=book, check=check)


def _generate(*, root: Path, book: str | None, check: bool) -> int:
    expected = expected_files(root, book)
    stale = stale_files(expected)

    if check and stale:
        for path in stale:
            print(
                f"error: generated Lean assembly is stale: {path.relative_to(root)}",
                file=sys.stderr,
            )
        return 1

    if not check:
        write_updates({path: expected[path] for path in stale})

    action = "Validated" if check else "Generated"
    print(f"{action} {len(expected)} Lean aggregation file(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        return generate(book=args.book, check=args.check)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
