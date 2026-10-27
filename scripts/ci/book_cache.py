"""Fingerprint committed book and shared build inputs for incremental CI caches."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.repository.config.validation_patterns import validation_pattern
from scripts.repository.path_policy import SHARED_BUILD_INPUT_ROOTS, book_input_prefix

ROOT = Path(__file__).resolve().parents[2]
POLICY = "book-inputs-v3"


@dataclass(frozen=True)
class BookInputs:
    book: str
    source_digest: str
    metadata_source: str
    policy: str = POLICY

    def fingerprint(self) -> str:
        descriptor = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(descriptor.encode("utf-8")).hexdigest()


def describe_inputs(book: str, *, root: Path = ROOT) -> BookInputs:
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
            book_input_prefix(book),
            *SHARED_BUILD_INPUT_ROOTS,
        ],
        cwd=root,
    )
    # Generated book.tex projects publication metadata; automation flags and
    # other books' registry records cannot change this book's compiler inputs.
    records = b"".join(
        record + b"\0"
        for record in records.split(b"\0")
        if record and record.partition(b"\t")[2] != b"config/books.yml"
    )
    return BookInputs(
        book,
        hashlib.sha256(records).hexdigest(),
        f"{book_input_prefix(book)}book.tex",
    )


def fingerprint(book: str, *, root: Path = ROOT) -> str:
    return describe_inputs(book, root=root).fingerprint()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument("--format", choices=("hash", "json"), default="hash")
    arguments = parser.parse_args()
    try:
        inputs = describe_inputs(arguments.book)
        if arguments.format == "json":
            print(
                json.dumps(
                    {**asdict(inputs), "fingerprint": inputs.fingerprint()},
                    sort_keys=True,
                )
            )
        else:
            print(inputs.fingerprint())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
