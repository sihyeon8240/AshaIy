"""Normalize final newlines without decoding or rewriting source contents."""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

FORMATTED = (
    "scripts/ashaiy",
    "scripts/*.py",
    "tests/*.py",
    "scripts/*.sh",
    "*.tex",
    "*.sty",
)


def normalized_bytes(source: bytes, *, collapse: bool = False) -> bytes:
    if not source:
        return source
    if collapse:
        source = re.sub(rb"\n(?:[ \t]*\n){2,}", b"\n\n", source)
    return source.rstrip(b"\t\r\n ") + b"\n"


def tracked_text_files(*, exclude_formatted: bool) -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z", "--cached"])
    files = []
    for name in output.split(b"\0"):
        if not name:
            continue
        path = Path(os.fsdecode(name))
        if not path.is_file():
            continue
        if exclude_formatted and any(fnmatch.fnmatchcase(str(path), pattern) for pattern in FORMATTED):
            continue
        # Match the text-only discovery policy; explicit files remain byte-oriented.
        if subprocess.run(["grep", "-Iq", "", "--", str(path)], check=False).returncode == 0:
            files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--exclude-formatted", action="store_true")
    parser.add_argument("--collapse-blank-lines", action="store_true")
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args()
    if args.exclude_formatted and (not args.check or args.files):
        parser.error("--exclude-formatted requires --check without file arguments")
    try:
        files = args.files or tracked_text_files(exclude_formatted=args.exclude_formatted)
        status = 0
        for path in files:
            original = path.read_bytes()
            normalized = normalized_bytes(original, collapse=args.collapse_blank_lines)
            if normalized == original:
                continue
            if args.check:
                print(f"needs whitespace normalization: {path}", file=sys.stderr)
                status = 1
            else:
                path.write_bytes(normalized)
        return status
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
