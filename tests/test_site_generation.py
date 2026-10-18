"""Deterministic site generation tests."""

from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "site_generator", REPO_ROOT / "scripts/site_pages.py"
)
assert spec and spec.loader
site_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_generator)


class SiteGenerationTests(unittest.TestCase):
    def manifest(self) -> dict:
        return {
            "books": [
                {
                    "slug": "alpha",
                    "title": "Alpha",
                    "status": "review",
                    "order": 10,
                    "site": True,
                    "release": False,
                },
                {
                    "slug": "beta",
                    "title": "Beta",
                    "status": "archived",
                    "order": 20,
                    "site": True,
                    "release": True,
                },
                {
                    "slug": "hidden",
                    "title": "Hidden",
                    "status": "draft",
                    "order": 30,
                    "site": False,
                },
            ]
        }

    def test_site_books_include_lean_coverage(self) -> None:
        metrics = {
            "verified": 2,
            "total": 8,
            "percentage": 25.0,
        }
        with mock.patch.object(
            site_generator, "book_lean_metrics", return_value=metrics
        ):
            books = site_generator.site_books(self.manifest())

        self.assertEqual(books[0]["lean_verified"], 2)
        self.assertEqual(books[0]["lean_total"], 8)
        self.assertEqual(books[0]["lean_coverage"], 25.0)

    def test_pdf_revision_is_shared_and_changes_with_source_checkout(self) -> None:
        for revision in ("a" * 40, "b" * 40):
            with (
                self.subTest(revision=revision),
                mock.patch.object(
                    site_generator, "snapshot_revision", return_value=revision
                ) as source,
            ):
                books = site_generator.site_books(self.manifest())

            source.assert_called_once_with()
            self.assertEqual(
                [book["snapshot_revision"] for book in books], [revision] * 2
            )
            self.assertEqual([book["release"] for book in books], [False, True])

    def test_exported_sources_can_render_without_git_metadata(self) -> None:
        with mock.patch.object(
            site_generator.subprocess,
            "run",
            side_effect=subprocess.CalledProcessError(128, "git"),
        ):
            self.assertEqual(site_generator.snapshot_revision(), "")

    def test_check_rejects_missing_pages_directory_without_creating_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pages_dir = root / "pages"
            with (
                mock.patch.object(
                    site_generator,
                    "load_manifest",
                    return_value=self.manifest(),
                ),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(
                    site_generator.generate(check=True, pages_dir=pages_dir), 1
                )
            self.assertFalse(pages_dir.exists())

    def test_check_rejects_stale_missing_and_orphaned_local_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pages_dir = Path(temporary) / "pages"
            pages_dir.mkdir()
            (pages_dir / "alpha.md").write_text("stale\n", encoding="utf-8")
            (pages_dir / "orphan.md").write_text("orphan\n", encoding="utf-8")
            with (
                mock.patch.object(
                    site_generator, "load_manifest", return_value=self.manifest()
                ),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(
                    site_generator.generate(check=True, pages_dir=pages_dir), 1
                )

    def test_single_book_updates_only_selected_page(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pages_dir = root / "pages"
            pages_dir.mkdir()
            (pages_dir / "beta.md").write_text("unchanged\n", encoding="utf-8")
            with (
                mock.patch.object(
                    site_generator, "load_manifest", return_value=self.manifest()
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    site_generator.generate(
                        pages_dir=pages_dir,
                        book="alpha",
                    ),
                    0,
                )
            self.assertEqual(
                (pages_dir / "alpha.md").read_text(),
                site_generator.render_site_page(
                    site_generator.site_books(self.manifest())[0]
                ),
            )
            self.assertEqual((pages_dir / "beta.md").read_text(), "unchanged\n")

    def test_single_hidden_book_fails(self) -> None:
        with mock.patch.object(
            site_generator, "load_manifest", return_value=self.manifest()
        ):
            with self.assertRaisesRegex(ValueError, "not enabled for site"):
                site_generator.generate(book="hidden")

    def test_combined_generation_skips_hidden_book_without_touching_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pages = Path(temporary) / "pages"
            with mock.patch.object(
                site_generator, "load_manifest", return_value=self.manifest()
            ):
                for check in (False, True):
                    self.assertEqual(
                        site_generator.generate(
                            book="hidden",
                            pages_dir=pages,
                            check=check,
                            skip_disabled=True,
                        ),
                        0,
                    )
                with self.assertRaisesRegex(ValueError, "not registered"):
                    site_generator.generate(book="unknown", skip_disabled=True)
            self.assertFalse(pages.exists())


if __name__ == "__main__":
    unittest.main()
