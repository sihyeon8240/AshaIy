#!/usr/bin/env python3
"""Check the pinned container toolchain and native executable caches."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ELF_MACHINES = {3: "x86", 40: "arm", 62: "amd64", 183: "arm64"}
HOST_ARCHITECTURES = {"x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}


def elf_architecture(path: Path) -> str | None:
    with path.open("rb") as stream:
        header = stream.read(20)
    if len(header) < 20 or header[:4] != b"\x7fELF" or header[5] not in (1, 2):
        return None
    byteorder = "little" if header[5] == 1 else "big"
    machine = int.from_bytes(header[18:20], byteorder)
    return ELF_MACHINES.get(machine, f"ELF machine {machine}")


def native_environment_errors(root: Path) -> list[str]:
    machine = platform.machine()
    expected = HOST_ARCHITECTURES.get(machine, machine)
    print(f"Platform: {platform.system()}/{expected}")
    targets = {Path(sys.executable): "Python"}
    for name in ("lean", "lake"):
        executable = shutil.which(name)
        if executable:
            targets[Path(executable)] = name
    if shutil.which("elan"):
        selected = subprocess.run(
            ["elan", "which", "lean"],
            cwd=root / "lean",
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        path = Path(selected.stdout.strip())
        if selected.returncode == 0 and path.is_file():
            targets[path] = "selected Lean toolchain"

    patterns = {
        "cached Lake executable": "lean/.lake/build/bin/*",
        "cached dependency executable": "lean/.lake/packages/*/.lake/build/bin/*",
    }
    for label, pattern in patterns.items():
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                targets[path] = label

    errors = []
    for path, label in targets.items():
        architecture = elf_architecture(path)
        if architecture is None:
            continue
        print(f"{label}: {architecture} ({path})")
        if architecture != expected:
            errors.append(
                f"{label} targets {architecture}, host is {expected}: {path}; "
                "rebuild the named Lake executable or reopen the container for "
                "the current architecture; see "
                "docs/developer-workflow.md#switching-container-architectures"
            )
    return errors


def main() -> int:
    print("[Development environment]", flush=True)
    errors = native_environment_errors(ROOT)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    sys.stdout.flush()
    status = subprocess.run([str(ROOT / "scripts/toolchain/check_toolchain.sh")], cwd=ROOT, check=False).returncode
    if status:
        return status

    print("\n[Repository]")
    for name in (
        "scripts/ashaiy",
        "config/latexmkrc",
        "books",
        "common",
        "common/styles/textbook.sty",
    ):
        if not (ROOT / name).exists():
            raise ValueError(f"{name} missing")
        print(f"  ✓ {name} found")

    print("\n[Versions]")
    commands = {
        "LuaLaTeX": ["lualatex", "--version"],
        "latexmk": ["latexmk", "-v"],
        "Biber": ["biber", "--version"],
        "Lean": ["lean", "--version"],
        "Lake": ["lake", "--version"],
        "Elan": ["elan", "--version"],
        "Python": [sys.executable, "--version"],
        "CLI": [str(ROOT / "scripts/ashaiy"), "--version"],
        "Git": ["git", "--version"],
        "ripgrep": ["rg", "--version"],
        "Ghostscript": ["gs", "--version"],
    }
    for label, command in commands.items():
        directory = ROOT / "lean" if label in {"Lean", "Lake"} else ROOT
        output = subprocess.check_output(command, cwd=directory, text=True)
        print(f"  {label:12}: {output.splitlines()[0]}")
    packages = json.loads((ROOT / "lean/lake-manifest.json").read_text())["packages"]
    mathlib = next(package for package in packages if package["name"] == "mathlib")
    print(f"  Mathlib     : {mathlib['inputRev']} ({mathlib['rev'][:12]})")
    print(f"  PyYAML      : {importlib.metadata.version('PyYAML')}")
    print("\nEnvironment is ready.")
    return 0


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
