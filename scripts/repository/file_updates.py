"""Serialize source updates and replace complete files with guarded recovery."""

from __future__ import annotations

import fcntl
import json
import os
import stat
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class UpdateScope:
    root: Path
    process: int = field(default_factory=os.getpid)
    observed: dict[Path, bytes | None] = field(default_factory=dict)


_active: ContextVar[UpdateScope | None] = ContextVar("source_updates", default=None)


def contents(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def observe_source(path: Path, data: bytes | None) -> None:
    scope = _active.get()
    if scope is None:
        return
    path = path.resolve()
    if path in scope.observed and scope.observed[path] != data:
        raise ValueError(f"source changed while planning updates: {path}")
    scope.observed[path] = data


def read_source(path: Path, *, errors: str = "strict") -> str:
    if _active.get() is None:
        return path.read_text(encoding="utf-8", errors=errors)
    data = path.read_bytes()
    observe_source(path, data)
    return data.decode("utf-8", errors=errors).replace("\r\n", "\n").replace("\r", "\n")


@contextmanager
def source_updates(root: Path, *, check: bool = False) -> Iterator[None]:
    root = root.resolve()
    scope = _active.get()
    if check or (
        scope is not None and scope.root == root and scope.process == os.getpid()
    ):
        yield
        return

    directory = root / "build/locks"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "source-updates.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        token = _active.set(UpdateScope(root))
        try:
            yield
        finally:
            _active.reset(token)


def validate_sources() -> None:
    scope = _active.get()
    if scope is not None:
        for path, original in scope.observed.items():
            if contents(path) != original:
                raise ValueError(f"source changed while planning updates: {path}")


def replace_file(
    path: Path,
    data: bytes,
    *,
    expected: bytes | None,
    durable: bool = False,
) -> None:
    # Preserve existing symlinks by replacing their target, as direct writes do.
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".ashaiy-{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            if durable:
                os.fsync(stream.fileno())
        if contents(path) != expected:
            raise ValueError(f"source changed before replacement: {path}")
        os.replace(temporary, path)
        scope = _active.get()
        if scope is not None:
            scope.observed[path] = data
        if durable:
            descriptor = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def retain_recovery(originals: Mapping[Path, bytes | None]) -> Path:
    scope = _active.get()
    parent = None
    if scope is not None:
        parent = scope.root / "build/recovery"
        parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="source-updates-", dir=parent))
    records = []
    for index, (path, original) in enumerate(originals.items()):
        backup = None
        if original is not None:
            backup = f"{index}.original"
            (directory / backup).write_bytes(original)
        records.append({"path": str(path.resolve()), "backup": backup})
    (directory / "files.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )
    return directory


def changed_files(updates: Mapping[Path, str]) -> list[Path]:
    changed = []
    for path, expected in updates.items():
        original = contents(path)
        observe_source(path, original)
        if original is None or (
            original.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
            != expected
        ):
            changed.append(path)
    return changed


def write_updates(updates: Mapping[Path, str], *, durable: bool = False) -> list[Path]:
    changed = changed_files(updates)
    originals = {path: contents(path) for path in changed}
    validate_sources()
    attempted: list[Path] = []

    try:
        for path in changed:
            attempted.append(path)
            replace_file(
                path,
                updates[path].encode("utf-8"),
                expected=originals[path],
                durable=durable,
            )
    except BaseException as error:
        failed = []
        for path in reversed(attempted):
            original = originals[path]
            try:
                current = contents(path)
                if current == original:
                    continue
                if current != updates[path].encode("utf-8"):
                    raise ValueError(f"source changed before recovery: {path}")
                if original is None:
                    path.unlink()
                    scope = _active.get()
                    if scope is not None:
                        scope.observed[path.resolve()] = None
                else:
                    replace_file(path, original, expected=current, durable=durable)
            except BaseException:
                failed.append(path)
        if failed:
            recovery = retain_recovery({path: originals[path] for path in failed})
            raise OSError(
                f"source update recovery failed for {failed}; originals retained at {recovery}"
            ) from error
        raise

    return changed
