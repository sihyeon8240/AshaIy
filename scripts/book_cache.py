"""Fingerprint committed book and shared build inputs for incremental CI caches."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validation_patterns import validation_pattern

ROOT = Path(__file__).resolve().parent.parent


def fingerprint(book: str, *, root: Path = ROOT) -> str:
    if not re.fullmatch(validation_pattern("book_slug"), book):
        raise ValueError("invalid book slug")
    if not (root / "books" / book / "book.tex").is_file():
        raise ValueError(f"missing book entry point: {book}")
    # Include shared directories conservatively, including future build helpers.
    # Git records bind paths, file modes, and content without checkout timestamps.
    records = subprocess.check_output(
        [
            "git",
            "ls-tree",
            "-r",
            "-z",
            "HEAD",
            "--",
            f"books/{book}",
            "common",
            "config",
            "scripts",
        ],
        cwd=root,
    )
    return hashlib.sha256(records).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    arguments = parser.parse_args()
    try:
        print(fingerprint(arguments.book))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
