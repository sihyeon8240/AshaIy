"""Validate rendered links and snapshot PDF bytes before upload."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.site.check_site_output import check


class SiteOutputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.site = self.root / "site"
        self.snapshot = self.root / "snapshot"
        for path in ("assets", "books", "pdf"):
            (self.site / path).mkdir(parents=True)
        (self.snapshot / "pdf").mkdir(parents=True)
        self.book_data = self.root / "books.json"
        self.book_data.write_text(json.dumps({"schema_version": 1, "books": [{"slug": "sample"}]}))
        (self.site / "index.html").write_text(
            '<article data-book-slug="sample"></article><link href="/math/assets/site.css" rel="stylesheet">'
            '<a href="/math/books/sample.html#reading">Read</a>'
            '<a href="/math/pdf/sample.pdf?v=abc">PDF</a>'
            '<a href="https://example.com/">External</a>'
        )
        (self.site / "books/sample.html").write_text(
            '<h1 id="reading">Read</h1><object data="../pdf/sample.pdf?v=abc"></object>'
        )
        (self.site / "assets/site.css").write_text('body { background: url("icon.svg"); }')
        (self.site / "assets/icon.svg").write_text("<svg></svg>")
        for directory in (self.site, self.snapshot):
            (directory / "pdf/sample.pdf").write_bytes(b"%PDF-1.7\nchecked PDF")

    def validate(self):
        with contextlib.redirect_stdout(io.StringIO()):
            check(self.site, self.snapshot, book_data=self.book_data, base_path="/math")

    def test_complete_site_resolves_html_css_images_and_versioned_pdfs(self):
        self.validate()

    def test_missing_link_targets_and_anchors_are_rejected(self):
        for target in (
            "assets/icon.svg",
            "assets/site.css",
            "pdf/sample.pdf",
            "books/sample.html",
        ):
            with self.subTest(target=target):
                path = self.site / target
                content = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, "missing local link target"):
                    self.validate()
                path.write_bytes(content)
        (self.site / "books/sample.html").write_text("<h1>No anchor</h1>")
        with self.assertRaisesRegex(ValueError, "missing HTML anchor"):
            self.validate()

    def test_pdf_corruption_and_non_pdf_content_are_rejected(self):
        (self.site / "pdf/sample.pdf").write_bytes(b"%PDF-1.7\ncorrupt")
        with self.assertRaisesRegex(ValueError, "differs from the snapshot"):
            self.validate()
        for directory in (self.site, self.snapshot):
            (directory / "pdf/sample.pdf").write_bytes(b"not a PDF")
        with self.assertRaisesRegex(ValueError, "invalid PDF header"):
            self.validate()

    def test_wrong_base_path_and_links_outside_output_are_rejected(self):
        for link in ("/pdf/sample.pdf", "../../outside.html"):
            with self.subTest(link=link):
                (self.site / "index.html").write_text(f'<a href="{link}">Bad</a>')
                with self.assertRaisesRegex(ValueError, "outside|escapes"):
                    self.validate()

    def test_unlinked_missing_pages_and_duplicate_cards_are_rejected(self):
        for failure in ("cards", "books", "pdf", "duplicate", "detail PDF"):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as temporary,
            ):
                destination = Path(temporary) / "site"
                shutil.copytree(self.site, destination)
                index = destination / "index.html"
                detail = destination / "books/sample.html"
                if failure == "cards":
                    index.write_text(index.read_text().replace('data-book-slug="sample"', 'data-other="sample"'))
                elif failure == "books":
                    detail.unlink()
                    index.write_text(
                        '<article data-book-slug="sample"></article><a href="/math/pdf/sample.pdf">PDF</a>'
                    )
                elif failure == "pdf":
                    (destination / "pdf/sample.pdf").unlink()
                    index.write_text(
                        '<article data-book-slug="sample"></article><a href="/math/books/sample.html">Details</a>'
                    )
                    detail.write_text("<h1>Details</h1>")
                elif failure == "duplicate":
                    index.write_text(index.read_text() + '<article data-book-slug="sample"></article>')
                else:
                    detail.write_text('<h1 id="reading">Details</h1>')
                with self.assertRaisesRegex(ValueError, "differ|missing detail page"):
                    check(
                        destination,
                        self.snapshot,
                        book_data=self.book_data,
                        base_path="/math",
                    )
