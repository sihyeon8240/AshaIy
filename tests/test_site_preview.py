"""Local preview PDF selection, tool requirements, and Make command routing."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "site_preview", ROOT / "scripts/site_preview.py"
)
assert spec and spec.loader
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class SitePreviewTests(unittest.TestCase):
    def test_missing_tool_fails_before_tests_can_skip(self) -> None:
        with mock.patch.object(preview.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "required tool not found: jekyll"):
                preview.test()

    def test_missing_and_empty_pdfs_leave_existing_site_intact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "build/site-preview/index.html"
            output.parent.mkdir(parents=True)
            output.write_text("previous preview")
            pdf = root / "build/alpha/book.pdf"
            pdf.parent.mkdir(parents=True)
            books = {"books": [{"slug": "alpha", "site": True}]}
            with (
                mock.patch.object(preview, "ROOT", root),
                mock.patch.object(preview, "require_tool", return_value="jekyll"),
                mock.patch.object(preview, "load_manifest", return_value=books),
                mock.patch.object(preview.subprocess, "run") as run,
            ):
                for empty in (False, True):
                    if empty:
                        pdf.touch()
                    with self.assertRaisesRegex(
                        ValueError, "ashaiy book build --book alpha"
                    ):
                        preview.build()
                    self.assertEqual(output.read_text(), "previous preview")
                run.assert_not_called()

    def test_build_stages_only_site_books_and_removes_stale_pdfs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "build/site-preview/pdf"
            output.mkdir(parents=True)
            (output / "old.pdf").write_bytes(b"old")
            pdf = root / "build/alpha/book.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"local PDF")
            books = {
                "books": [
                    {"slug": "alpha", "site": True},
                    {"slug": "beta", "site": False},
                ]
            }
            with (
                mock.patch.object(preview, "ROOT", root),
                mock.patch.object(preview, "require_tool", return_value="jekyll"),
                mock.patch.object(preview, "load_manifest", return_value=books),
                mock.patch.object(preview.subprocess, "run"),
            ):
                preview.build()
            self.assertEqual([path.name for path in output.iterdir()], ["alpha.pdf"])
            self.assertEqual((output / "alpha.pdf").read_bytes(), pdf.read_bytes())
