#!/usr/bin/env python3
"""Bind retained release bytes to their validated source run."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from github_artifacts import checksum, command


def record(book: str, directory: Path) -> None:
    packages = list(directory.glob(f"{book}-v*.pdf"))
    if len(packages) != 1:
        raise ValueError("expected exactly one original release PDF")
    pdf = packages[0]
    version = pdf.name.removeprefix(f"{book}-v").removesuffix(".pdf")
    files = (pdf.name, "SHA256SUMS")
    source = command("git", "rev-parse", "HEAD").decode().strip()
    if source != os.environ["GITHUB_SHA"]:
        raise ValueError("release checkout differs from the validated source")
    manifest = {
        "policy": "release-package-v1",
        "book": book,
        "version": version,
        "source_sha": source,
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "checksums": {name: checksum(directory / name) for name in files},
    }
    (directory / "release-build.json").write_text(json.dumps(manifest) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    record(args.book, args.directory)


if __name__ == "__main__":
    main()
