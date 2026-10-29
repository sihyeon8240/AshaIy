#!/usr/bin/env python3
"""Describe the PDF build environment and invalidate stale incremental outputs."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
from pathlib import Path

POLICY = "pdf-environment-v1"
FILENAME = "book.build-environment.json"
SEARCH_VARIABLES = (
    "TEXINPUTS",
    "BIBINPUTS",
    "BSTINPUTS",
    "LUAINPUTS",
    "OSFONTDIR",
    "TEXMFHOME",
    "TEXMFVAR",
    "TEXMFCACHE",
)


def canonical_environment(root: Path) -> dict[str, str]:
    toolchain = (root / "config/toolchain.env").read_text(encoding="utf-8")
    match = re.search(r"^TEXLIVE_ARCHIVE_DATE=(\d{4}/\d{2}/\d{2})$", toolchain, re.M)
    if match is None:
        raise ValueError("missing TeX Live archive date")
    date = datetime.datetime.strptime(match[1], "%Y/%m/%d").replace(tzinfo=datetime.timezone.utc)
    return {
        "policy": POLICY,
        "SOURCE_DATE_EPOCH": str(int(date.timestamp())),
        "FORCE_SOURCE_DATE": "1",
        "TZ": "UTC",
        "LC_ALL": "C.UTF-8",
        "SHELL_ESCAPE": "0",
        **dict.fromkeys(SEARCH_VARIABLES, ""),
    }


def selected_environment(root: Path, environ: dict[str, str]) -> dict[str, str]:
    environment = canonical_environment(root)
    for name in ("SOURCE_DATE_EPOCH", "SHELL_ESCAPE", *SEARCH_VARIABLES):
        if name in environ:
            environment[name] = environ[name]
    prefix = f".:{root}/common/styles//:{root}/common/templates//:"
    while environment["TEXINPUTS"].startswith(prefix):
        environment["TEXINPUTS"] = environment["TEXINPUTS"][len(prefix) :]
    if not re.fullmatch(r"[0-9]+", environment["SOURCE_DATE_EPOCH"]):
        raise ValueError("SOURCE_DATE_EPOCH must be a nonnegative integer")
    if environment["SHELL_ESCAPE"] not in {"0", "1"}:
        raise ValueError("SHELL_ESCAPE must be 0 or 1")
    return environment


def prepare(directory: Path, environment: dict[str, str], document: str) -> bool:
    if Path(document).name != document:
        raise ValueError("a document filename is required")
    name = f"{Path(document).stem}.build-environment.json"
    path = directory / name
    serialized = json.dumps(environment, sort_keys=True) + "\n"
    changed = not path.exists() or path.read_text(encoding="utf-8") != serialized
    # The caller holds the output-directory lock across this write and latexmk.
    (directory / f".{name}.pending").write_text(serialized, encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("document")
    args = parser.parse_args()
    try:
        environment = selected_environment(args.root, dict(os.environ))
        changed = prepare(args.directory, environment, args.document)
    except (ValueError, OSError) as error:
        parser.exit(2, f"error: {error}\n")
    print(environment["SOURCE_DATE_EPOCH"], int(changed))


if __name__ == "__main__":
    main()
