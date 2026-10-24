"""Run repository metadata checks with one reusable source snapshot."""

from __future__ import annotations

import argparse
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import (
    architecture_checks,
    contents_generation,
    documentation_checks,
    label_checks,
    lean_generation,
    proof_links,
    site_pages,
)
from scripts.book_manifest import load_manifest, manifest_warnings
from scripts.config_sync import synchronize
from scripts.repository_config import load_image
from scripts.source_reads import reuse_source_reads

ROOT = Path(__file__).resolve().parent.parent


def check_repository_files() -> None:
    required = (
        "scripts/ashaiy",
        "config/pyproject.toml",
        "config/container-image.txt",
        "config/toolchain.env",
        "README.md",
        "docs/CONTRIBUTING.md",
        "scripts/format_python.sh",
        "scripts/format_code.py",
        "scripts/source_checks.py",
        "scripts/source_reads.py",
        "scripts/build_support.sh",
        "scripts/format_shell.sh",
        "common/styles/textbook.sty",
        "common/styles/bibliography.sty",
        "common/styles/core.sty",
        "common/styles/math.sty",
        "common/styles/theorems.sty",
        "scripts/build_book.sh",
        "scripts/check_actions.sh",
        "scripts/check_lean.sh",
        "scripts/check_proof_links.py",
        "scripts/check_image_reference.py",
        "scripts/config_sync.py",
        "scripts/export_config.sh",
        "scripts/repository_config.py",
        "scripts/upload_release_assets.sh",
        "scripts/releases.py",
        "scripts/release_plan.sh",
        "scripts/package_book.sh",
        "scripts/publish_release.sh",
        "lean/lean-toolchain",
        "lean/lakefile.toml",
        "lean/Textbooks.lean",
    )
    for name in required:
        if not (ROOT / name).exists():
            raise ValueError(f"required repository path is missing: {name}")

    for path in sorted((ROOT / "scripts").rglob("*.py")):
        py_compile.compile(str(path), doraise=True)

    if subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode:
        print(
            "warning: Git metadata unavailable; skipped tracked generated-file check",
            file=sys.stderr,
        )
        return
    pattern = re.compile(
        r"(^|/)(vscode-build|build|dist|\.lake|\.cache|context.tex|tree.txt)/"
        r"|\.(aux|bbl|bcf|blg|fdb_latexmk|fls|idx|ilg|ind|lof|log|lot|out|pdf|pyc"
        r"|run\.xml|synctex\.gz|toc|xdv)$"
    )
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    generated = [
        os.fsdecode(name)
        for name in output.split(b"\0")
        if name and pattern.search(os.fsdecode(name))
    ]
    if generated:
        raise ValueError("generated files are tracked:\n" + "\n".join(generated))


def check_sources(*, defer: str | None = None) -> int:
    with reuse_source_reads():
        manifest = load_manifest()
        for warning in manifest_warnings(manifest):
            print(f"warning: {warning}", file=sys.stderr)
        print("config/books.yml is valid")

        if contents_generation.generate("all", check=True):
            return 1
        if defer != "lean" and lean_generation.generate(check=True):
            return 1

        if architecture_checks.check_architecture():
            return 1
        if documentation_checks.main():
            return 1

        with tempfile.TemporaryDirectory() as temporary:
            if site_pages.generate(pages_dir=Path(temporary), verify_output=True):
                return 1

        stale = synchronize(check=True)
        if stale:
            for path in stale:
                print(
                    f"error: synchronized configuration is stale: {path}",
                    file=sys.stderr,
                )
            return 1
        print(f"Textbook build image is synchronized: {load_image()}")

        if defer is None and proof_links.check_proof_links():
            return 1

        files = sorted(
            path
            for directory in (ROOT / "books", ROOT / "common/templates")
            for path in directory.rglob("*.tex")
        )
        status = label_checks.check_labels(files)
        if status:
            return status
        check_repository_files()
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    defer = parser.add_mutually_exclusive_group()
    defer.add_argument(
        "--defer-proof-links", dest="defer", action="store_const", const="proof-links"
    )
    defer.add_argument("--defer-lean", dest="defer", action="store_const", const="lean")
    args = parser.parse_args()

    try:
        return check_sources(defer=args.defer)
    except (
        OSError,
        UnicodeError,
        ValueError,
        py_compile.PyCompileError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
