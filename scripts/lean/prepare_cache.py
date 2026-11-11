#!/usr/bin/env python3
"""Download the project's Mathlib imports and rebuild foreign native cache tools."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.lean.lean_source import imports
from scripts.toolchain.check_environment import cached_lake_executables, elf_architecture, host_architecture

ROOT = Path(__file__).resolve().parents[2]
NATIVE_TARGETS = {
    "packages/mathlib/.lake/build/bin/cache": "@mathlib/cache",
    "packages/batteries/.lake/build/bin/runLinter": "@batteries/runLinter",
    "packages/importGraph/.lake/build/bin/graph": "@importGraph/graph",
}


def project_mathlib_imports(root: Path) -> list[str]:
    pending = ["Textbooks"]
    visited = set()
    mathlib = set()
    lean = root / "lean"
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        visited.add(module)
        source = lean.joinpath(*module.split(".")).with_suffix(".lean")
        if not source.resolve().is_relative_to(lean.resolve()):
            raise ValueError(f"project import escapes lean/: {module}")
        for dependency, _ in imports(source.read_text(encoding="utf-8")):
            if dependency == "Mathlib" or dependency.startswith("Mathlib."):
                mathlib.add(dependency)
            elif dependency.startswith("Textbooks."):
                pending.append(dependency)
    return sorted(mathlib)


def repair_native_executables(root: Path) -> None:
    expected = host_architecture()
    lake = root / "lean/.lake"
    for path in cached_lake_executables(root):
        if not path.is_file():
            continue
        architecture = elf_architecture(path)
        if architecture is None or architecture == expected:
            continue
        relative = path.relative_to(lake).as_posix()
        target = NATIVE_TARGETS.get(relative)
        if target is None or path.is_symlink() or not path.resolve().is_relative_to(lake.resolve()):
            raise ValueError(f"foreign cached executable preserved; rebuild it manually for {expected}: {path}")
        print(f"Rebuilding {target}: {architecture} -> {expected}", flush=True)
        command = ["lake", "--no-cache", "build", target]
        subprocess.run(command, cwd=root / "lean", check=True)
        if elf_architecture(path) == expected:
            continue

        # A restored executable trace may still mark the foreign binary up to date.
        path.unlink()
        path.with_name(path.name + ".trace").unlink(missing_ok=True)
        subprocess.run(command, cwd=root / "lean", check=True)
        if elf_architecture(path) != expected:
            raise ValueError(f"rebuilt executable still does not target {expected}: {path}")


def prepare(root: Path = ROOT) -> None:
    modules = project_mathlib_imports(root)
    if not modules:
        print("No Mathlib imports to prepare.")
        return
    repair_native_executables(root)
    print(f"Preparing cache for {len(modules)} direct Mathlib import(s).", flush=True)
    subprocess.run(
        ["lake", "exe", "cache", "get", *modules],
        cwd=root / "lean",
        env={**os.environ, "MATHLIB_NO_CACHE_ON_UPDATE": "1"},
        check=True,
    )
    repair_native_executables(root)
    print("Lean cache is ready.", flush=True)


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        prepare()
    except subprocess.CalledProcessError as error:
        return error.returncode
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
