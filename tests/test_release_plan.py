"""Behavior tests for release tag planning."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_support import (
    book_record,
    copy_validation_configuration,
    manifest_document,
    write_yaml,
)

ROOT = Path(__file__).resolve().parent.parent


class ReleasePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        copy_validation_configuration(self.root)
        scripts = self.root / "scripts"
        scripts.mkdir(exist_ok=True)
        shutil.copy2(ROOT / "scripts/release_plan.sh", scripts / "release_plan.sh")
        for name in (
            "releases.py",
            "book_manifest.py",
            "contents_manifest.py",
            "latex_scan.py",
            "latex_titles.py",
            "source_reads.py",
        ):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)

    def run_plan(
        self, tag: str, **environment: str
    ) -> subprocess.CompletedProcess[str]:
        slugs = environment.get("RELEASABLE", "alpha").split()
        version = environment.get("VERSION", "1.2.3")
        records = []
        for number, slug in enumerate(slugs):
            (self.root / "books" / slug).mkdir(parents=True, exist_ok=True)
            (self.root / "books" / slug / "book.tex").write_text("")
            records.append(
                book_record(slug, version=version, release=True, order=number)
            )
        write_yaml(self.root / "config/books.yml", manifest_document(records))
        return subprocess.run(
            [str(self.root / "scripts/release_plan.sh"), tag],
            cwd=self.root,
            env={**os.environ, "PYTHON": sys.executable, **environment},
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def test_valid_tag_exports_version_and_single_book_matrix(self) -> None:
        result = self.run_plan("alpha-v1.2.3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["alpha_version=1.2.3", "version=1.2.3", 'matrix={"book":["alpha"]}'],
        )

    def test_hyphenated_prerelease_tags_are_accepted(self) -> None:
        for version in (
            "1.2.3--alpha",
            "1.2.3-alpha--beta",
            "1.2.3-rc.1",
            "1.2.3-very-early",
        ):
            with self.subTest(version=version):
                result = self.run_plan(f"alpha-v{version}", VERSION=version)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"version={version}\n", result.stdout)

    def test_invalid_or_disabled_book_tag_is_rejected(self) -> None:
        invalid = self.run_plan("alpha-1.2.3")
        disabled = self.run_plan("beta-v1.2.3")
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("invalid release tag", invalid.stderr)
        self.assertEqual(disabled.returncode, 2)
        self.assertIn("not enabled for release", disabled.stderr)

    def test_manifest_version_must_match_tag(self) -> None:
        result = self.run_plan("alpha-v1.2.4", VERSION="1.2.3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("tag version 1.2.4 does not match", result.stderr)


if __name__ == "__main__":
    unittest.main()
