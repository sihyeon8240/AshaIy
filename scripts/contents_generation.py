#!/usr/bin/env python3
"""Generate LaTeX textbook assembly from chapters.yml and sections.yml."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.book_manifest import load_manifest
from scripts.contents_manifest import expected_files, proof_index_paths
from scripts.file_updates import changed_files, write_updates

ROOT = Path(__file__).resolve().parent.parent


def generate(scope: str, *, book: str | None = None, check: bool = False) -> int:
    manifest = load_manifest()
    selected = manifest["books"]
    if book:
        selected = [item for item in selected if item["slug"] == book]
        if not selected:
            raise ValueError(f"book is not registered in config/books.yml: {book}")

    updates: dict[Path, str] = {}
    proof_template = None
    for item in selected:
        book_dir = ROOT / "books" / item["slug"]
        updates.update(expected_files(book_dir, scope, book=item))
        if scope in {"sec", "all"}:
            for path in proof_index_paths(book_dir):
                if not path.exists():
                    if proof_template is None:
                        proof_template = (
                            ROOT / "common/templates/proofs.yml"
                        ).read_text(encoding="utf-8")
                    updates[path] = proof_template

    stale = changed_files(updates) if check else write_updates(updates)

    if check and stale:
        for path in stale:
            print(
                f"error: generated contents are stale: {path.relative_to(ROOT)}",
                file=sys.stderr,
            )
        return 1
    action = "Validated" if check else "Generated"
    print(f"{action} {len(updates)} contents file(s).")
    return 0


def main() -> int:
    from scripts.repository_cli import contents_main

    return contents_main()


if __name__ == "__main__":
    raise SystemExit(main())
