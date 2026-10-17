"""Apply precomputed text updates with rollback on write failure."""

from __future__ import annotations

from pathlib import Path


def changed_files(updates: dict[Path, str]) -> list[Path]:
    return [
        path
        for path, expected in updates.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != expected
    ]


def write_updates(updates: dict[Path, str]) -> list[Path]:
    changed = changed_files(updates)
    originals = {path: path.read_bytes() if path.exists() else None for path in changed}
    attempted: list[Path] = []

    try:
        for path in changed:
            attempted.append(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(updates[path], encoding="utf-8")
    except Exception:
        for path in reversed(attempted):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
        raise

    return changed
