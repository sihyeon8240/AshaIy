"""Fingerprint formatter implementations and policy for local and CI caches."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUTS = (
    "scripts/latex/format_cache.py",
    "scripts/latex/format_tex.py",
    "scripts/repository/formatting/normalize_eof.py",
    "scripts/latex/latex_scan.py",
    "scripts/latex/normalize_braces.py",
    "scripts/latex/command_specs.py",
    "scripts/latex/macro_manifest.py",
    "scripts/latex/macro_generation.py",
    "scripts/latex/theorem_manifest.py",
    "scripts/latex/theorem_generation.py",
    "scripts/repository/source_reads.py",
    "scripts/repository/processes.py",
    "scripts/books/book_manifest.py",
    "scripts/lean/lean_source.py",
    "scripts/latex/format_tex_file.sh",
    "config/latexindent.yaml",
    "common/styles/theorems.yml",
)


def fingerprint(root: Path = ROOT, *, observe: Callable[[Path, bytes], None] | None = None) -> str:
    digest = hashlib.sha256()
    for relative in INPUTS:
        path = root / relative
        contents = path.read_bytes()
        if observe is not None:
            observe(path, contents)
        digest.update(relative.encode() + b"\0")
        digest.update(hashlib.sha256(contents).digest())
    return digest.hexdigest()


if __name__ == "__main__":
    print(fingerprint())
