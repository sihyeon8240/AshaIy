"""Bound temporary bytecode while preserving shared interpreter caches."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def temporary_directory(*, prefix: str):
    with tempfile.TemporaryDirectory(prefix=prefix) as temporary:
        directory = Path(temporary)
        bytecode = (
            Path(importlib.util.cache_from_source(str(directory / "scratch.py"))).parent
            if sys.pycache_prefix is not None
            else None
        )
        try:
            yield directory
        finally:
            if bytecode is not None and bytecode.exists():
                shutil.rmtree(bytecode)


def prune(*, root: Path = ROOT, dry_run: bool = False) -> int:
    cache = root / ".cache/python"
    source = Path(tempfile.gettempdir()).absolute()
    temporary_cache = cache / source.relative_to(source.anchor)
    for path in (temporary_cache, *temporary_cache.parents):
        if path.is_symlink():
            raise ValueError(f"refusing symlinked cache path: {path}")
        if path == root:
            break
    removed = 0
    if temporary_cache.is_dir():
        for directory in sorted(temporary_cache.iterdir()):
            if directory.is_symlink() or not directory.is_dir() or os.path.lexists(source / directory.name):
                continue
            if dry_run:
                print(f"[py] would remove: {directory.relative_to(root)}")
            else:
                shutil.rmtree(directory)
            removed += 1
    action = "Would remove" if dry_run else "Removed"
    print(f"{action} {removed} stale temporary bytecode director{'y' if removed == 1 else 'ies'}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="list stale temporary bytecode without removing it")
    arguments = parser.parse_args()
    try:
        return prune(dry_run=arguments.dry_run)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
