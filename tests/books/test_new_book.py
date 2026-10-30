"""Textbook scaffold creation and failure rollback."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.support.fixtures import (
    book_record,
    copy_file,
    copy_validation_configuration,
    manifest_document,
    write_yaml,
)

ROOT = Path(__file__).resolve().parents[2]


class NewBookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        scripts = self.root / "scripts"
        scripts.mkdir(parents=True)
        for source in (ROOT / "scripts").rglob("*.py"):
            copy_file(source, self.root / source.relative_to(ROOT))
        shutil.copytree(ROOT / "common/templates", self.root / "common/templates")
        (self.root / "books").mkdir()
        copy_validation_configuration(self.root)
        write_yaml(self.root / "config/books.yml", manifest_document([]))

    def run_new(self, slug: str = "new-book", **environment: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.root / "scripts/books/new_book.py"),
                slug,
                "New Book",
            ],
            cwd=self.root,
            env={**os.environ, "PYTHON": sys.executable, **environment},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def test_success_creates_minimal_scaffold(self) -> None:
        result = self.run_new()
        target = self.root / "books/new-book"
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((target / "chapters/introduction/index.tex").is_file())
        self.assertFalse((target / "overrides").exists())
        self.assertFalse((target / "metadata.tex").exists())
        self.assertFalse((target / "overrides/style.sty").exists())
        self.assertTrue((target / "references.bib").is_file())
        self.assertEqual(
            (target / "formalization.md").read_text(),
            (ROOT / "common/templates/formalization.md").read_text(),
        )
        self.assertIn(
            "nb:sec:first-section",
            (target / "chapters/introduction/first-section.tex").read_text(),
        )
        self.assertIn("New Book", (target / "book.tex").read_text())
        self.assertIn(
            r"\input{chapters/introduction/first-section.tex}",
            (target / "chapters/introduction/index.tex").read_text(),
        )
        self.assertTrue((target / "chapters/introduction/proofs.yml").is_file())
        self.assertFalse((target / "README.md").exists())
        self.assertIn("ashaiy config generate", result.stdout)
        self.assertIn("ashaiy config check", result.stdout)
        self.assertIn(".vscode/tasks.json", result.stdout)

    def test_scaffold_stays_unpublished_under_every_publication_default(self) -> None:
        for release, site in (
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ):
            with self.subTest(release=release, site=site):
                path = self.root / "config/books.yml"
                write_yaml(path, manifest_document([], release=release, site=site))
                slug = f"new-book-{int(release)}-{int(site)}"
                result = self.run_new(slug)
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = yaml.safe_load(path.read_text())
                self.assertEqual(manifest["defaults"]["release"], release)
                self.assertEqual(manifest["defaults"]["site"], site)
                self.assertIs(manifest["books"][0]["release"], False)
                self.assertIs(manifest["books"][0]["site"], False)

    def test_existing_target_is_preserved(self) -> None:
        target = self.root / "books/new-book"
        target.mkdir()
        marker = target / "keep"
        marker.write_text("keep", encoding="utf-8")
        result = self.run_new()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(marker.is_file())

    def test_failure_after_creation_removes_partial_scaffold(self) -> None:
        original = (self.root / "config/books.yml").read_bytes()
        # Registration succeeds before contents validation discovers this error.
        (self.root / "common/templates/sections.yml").write_text("invalid: true\n")
        result = self.run_new()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse((self.root / "books/new-book").exists())
        self.assertIn("creation failed", result.stderr)
        self.assertEqual((self.root / "config/books.yml").read_bytes(), original)

    def test_failed_registration_restores_original_registry(self) -> None:
        existing = self.root / "books/new-background/book.tex"
        existing.parent.mkdir()
        existing.write_text("existing\n")
        write_yaml(
            self.root / "config/books.yml",
            manifest_document([book_record("new-background", label_prefix="nb")]),
        )
        original = (self.root / "config/books.yml").read_bytes()
        result = self.run_new()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("duplicate label_prefix", result.stderr)
        self.assertFalse((self.root / "books/new-book").exists())
        self.assertEqual((self.root / "config/books.yml").read_bytes(), original)
        self.assertEqual(existing.read_text(), "existing\n")


if __name__ == "__main__":
    unittest.main()
