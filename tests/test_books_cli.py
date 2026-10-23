"""Integration tests for the books.py command-line interface."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


class BooksCliTests(unittest.TestCase):
    def run_validate_new(
        self, slug: str, title: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts/books.py"),
                "validate-new",
                slug,
                title,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_validate_new_uses_manifest_input_rules(self) -> None:
        valid = self.run_validate_new("new-book", "New Book")
        self.assertEqual(valid.returncode, 0, valid.stderr)
        for slug, title in (("Bad_Slug", "Title"), ("good-slug", "line\nbreak")):
            with self.subTest(slug=slug, title=title):
                self.assertNotEqual(self.run_validate_new(slug, title).returncode, 0)


class ExportFixtureTests(unittest.TestCase):
    @staticmethod
    def book(slug: str, order: int, **overrides: object) -> dict[str, Any]:
        record: dict[str, Any] = {
            "slug": slug,
            "title": slug.title(),
            "version": "1.0.0",
            "status": "draft",
            "order": order,
        }
        record.update(overrides)
        return record

    def run_export(
        self,
        defaults: dict[str, Any],
        books: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as temporary:
            repository_root = Path(temporary)
            for book in books:
                slug = str(book["slug"])
                book_directory = repository_root / "books" / slug
                book_directory.mkdir(parents=True)
                (book_directory / "book.tex").write_text("", encoding="utf-8")
            manifest_path = repository_root / "config/books.yml"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "defaults": defaults,
                        "books": books,
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "books.py"),
                    "export",
                    "--for",
                    "site",
                    "--format",
                    "json",
                    "--manifest",
                    str(manifest_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_export_normalizes_filters_and_sorts_fixture(self) -> None:
        defaults = {
            "author": "Sample Author",
            "build": True,
            "check": False,
            "release": False,
            "site": True,
        }
        books = [
            self.book("zulu", 20, site=False),
            self.book("bravo", 10, build=True, release=True),
            self.book("alpha", 10),
        ]

        payload = self.run_export(defaults, books)

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(
            [book["slug"] for book in payload["books"]], ["alpha", "bravo"]
        )
        self.assertEqual(
            payload["books"][0],
            {
                "build": True,
                "check": False,
                "release": False,
                "site": True,
                "slug": "alpha",
                "label_prefix": "a",
                "author": "Sample Author",
                "version": "1.0.0",
                "title": "Alpha",
                "status": "draft",
                "order": 10,
            },
        )
        self.assertEqual(
            payload["books"][1],
            {
                "build": True,
                "check": False,
                "release": True,
                "site": True,
                "slug": "bravo",
                "label_prefix": "b",
                "author": "Sample Author",
                "version": "1.0.0",
                "title": "Bravo",
                "status": "draft",
                "order": 10,
            },
        )

    def test_book_can_enable_site_when_default_is_false(self) -> None:
        defaults = {
            "author": "Sample Author",
            "build": True,
            "check": True,
            "release": False,
            "site": False,
        }
        books = [self.book("hidden", 10), self.book("visible", 20, site=True)]

        payload = self.run_export(defaults, books)

        self.assertEqual([book["slug"] for book in payload["books"]], ["visible"])
        self.assertTrue(payload["books"][0]["site"])


if __name__ == "__main__":
    unittest.main()
