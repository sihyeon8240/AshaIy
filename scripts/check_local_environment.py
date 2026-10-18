#!/usr/bin/env python3
"""Check task dependencies without requiring the complete container image."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = {
    "pdf": ("bash", "git", "latexmk", "lualatex", "kpsewhich", "biber"),
    "lean": ("bash", "git", "elan", "lean", "lake"),
    "format": (
        "bash",
        "rg",
        "ruff",
        "shfmt",
        "shellcheck",
        "latexindent",
        "basedpyright",
        "yamllint",
        "check-jsonschema",
        "djlint",
    ),
    "site": ("ruby", "bundle", "jekyll"),
}


def check_full_environment() -> int:
    print(
        "\n==============================================\n Development Environment Check\n==============================================\n",
        flush=True,
    )
    status = subprocess.run(
        [str(ROOT / "scripts/check_toolchain.sh")], cwd=ROOT, check=False
    ).returncode
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
    (ROOT / "build").mkdir(exist_ok=True)
    print("\n  ✓ build/ is ready\n\n[Versions]")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=(*PROFILES, "full"))
    arguments = parser.parse_args()
    if arguments.profile == "full":
        return check_full_environment()
    errors = []

    if platform.system() != "Linux":
        errors.append("local support requires Linux or WSL2")
    if sys.version_info < (3, 14):
        errors.append("Python 3.14 or newer is required")
    try:
        print(f"PyYAML {importlib.metadata.version('PyYAML')}")
    except importlib.metadata.PackageNotFoundError:
        errors.append("PyYAML missing; run scripts/setup_local.sh")

    for command in PROFILES[arguments.profile]:
        executable = shutil.which(command)
        if executable:
            print(f"{command}: {executable}")
        else:
            errors.append(f"{command} missing")

    if arguments.profile == "pdf" and shutil.which("kpsewhich"):
        for filename in (
            "fontspec.sty",
            "biblatex.sty",
            "microtype.sty",
            "cleveref.sty",
        ):
            if subprocess.run(["kpsewhich", filename], capture_output=True).returncode:
                errors.append(f"TeX package missing: {filename}")

    if arguments.profile == "lean" and shutil.which("lean"):
        expected = (ROOT / "lean/lean-toolchain").read_text().strip().split(":")[-1]
        result = subprocess.run(
            ["lean", "--version"], cwd=ROOT / "lean", capture_output=True, text=True
        )
        if result.returncode or expected.removeprefix("v") not in result.stdout:
            errors.append(f"Lean {expected} required by lean/lean-toolchain")

    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"{arguments.profile} tools are ready; run the task to verify compatibility.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
