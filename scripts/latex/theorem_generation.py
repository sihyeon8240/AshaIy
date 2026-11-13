"""Generate the shared theorem package with guarded source updates."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.latex.theorem_manifest import TheoremManifest, load_theorems, render_theorems
from scripts.repository.file_updates import changed_files, source_updates, write_updates
from scripts.repository.source_reads import reuse_source_reads

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path("common/styles/theorems.yml")
GENERATED = Path("common/styles/generated-theorems.sty")


def package(root: Path) -> tuple[TheoremManifest, dict[Path, str]]:
    manifest = load_theorems(root / MANIFEST)
    return manifest, {root / GENERATED: render_theorems(manifest)}


def checked_manifest(root: Path) -> TheoremManifest:
    manifest, updates = package(root)
    if stale := changed_files(updates):
        raise ValueError(f"{stale[0]}: generated theorems are stale; run ashaiy theorems generate")
    return manifest


def generate(*, check: bool = False, root: Path = ROOT) -> int:
    with source_updates(root, check=check):
        with reuse_source_reads():
            _, updates = package(root)
        stale = changed_files(updates) if check else write_updates(updates)
        if check and stale:
            for path in stale:
                print(f"{path}: error: generated theorems are stale; run ashaiy theorems generate", file=sys.stderr)
            return 1
    print(f"{'Validated' if check else 'Generated'} shared theorem package.")
    return 0
