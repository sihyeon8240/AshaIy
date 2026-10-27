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
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.books import contents_generation
from scripts.books.book_manifest import load_manifest, manifest_warnings
from scripts.latex import label_checks, macro_generation
from scripts.lean import lean_generation, proof_links
from scripts.repository.checks import architecture_checks, documentation_checks
from scripts.repository.config.config_sync import synchronize
from scripts.repository.config.repository_config import load_image
from scripts.repository.source_reads import reuse_source_reads
from scripts.site import site_pages

ROOT = Path(__file__).resolve().parents[3]


def check_repository_files() -> None:
    required = (
        "scripts/ashaiy",
        "config/pyproject.toml",
        "config/container-image.txt",
        "config/toolchain.env",
        "README.md",
        "docs/CONTRIBUTING.md",
        "scripts/repository/formatting/format_code.py",
        "scripts/repository/checks/source_checks.py",
        "scripts/repository/source_reads.py",
        "scripts/latex/build_support.sh",
        "common/styles/textbook.sty",
        "common/styles/bibliography.sty",
        "common/styles/core.sty",
        "common/styles/macros.yml",
        "common/styles/generated-common-macros.sty",
        "common/styles/theorems.sty",
        "scripts/latex/build_book.sh",
        "scripts/repository/checks/check_actions.sh",
        "scripts/lean/check_lean.sh",
        "scripts/lean/proof_links.py",
        "scripts/toolchain/images/check_image_reference.py",
        "scripts/repository/config/config_sync.py",
        "scripts/repository/config/export_config.sh",
        "scripts/repository/config/repository_config.py",
        "scripts/release/upload_release_assets.sh",
        "scripts/release/releases.py",
        "scripts/release/release_plan.sh",
        "scripts/release/package_book.sh",
        "scripts/release/publish_release.sh",
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
        r"(^|/)(vscode-build|build|dist|\.lake|\.cache|\.hypothesis)/"
        r"|^site/(books/|_data/books\.json$)"
        r"|(^|/)(context\.tex|tree\.txt|__latexindent_temp_[^/]+\.tex)$"
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

        if macro_generation.generate(check=True):
            return 1
        if contents_generation.generate("all", check=True):
            return 1
        if defer != "lean" and lean_generation.generate(check=True):
            return 1

        if architecture_checks.check_architecture():
            return 1
        if documentation_checks.main():
            return 1

        with tempfile.TemporaryDirectory() as temporary:
            if site_pages.generate(site_dir=Path(temporary), verify_output=True):
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
