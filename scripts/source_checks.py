"""Run repository metadata checks with one reusable source snapshot."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

try:
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
except ModuleNotFoundError:
    import architecture_checks
    import contents_generation
    import documentation_checks
    import label_checks
    import lean_generation
    import proof_links
    import site_pages
    from book_manifest import load_manifest, manifest_warnings
    from config_sync import synchronize
    from repository_config import load_image
    from source_reads import reuse_source_reads

ROOT = Path(__file__).resolve().parent.parent


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
        return label_checks.check_labels(files)


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
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
