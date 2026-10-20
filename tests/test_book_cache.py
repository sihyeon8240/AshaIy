"""Book caches reuse unrelated commits and invalidate changed build inputs."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.book_cache import fingerprint


class BookCacheTests(unittest.TestCase):
    def test_committed_inputs_and_paths_determine_cache_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*arguments: str) -> None:
                subprocess.run(
                    ["git", *arguments], cwd=root, check=True, capture_output=True
                )

            def commit(path: str, text: str) -> str:
                source = root / path
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(text)
                git("add", "--", path)
                git("commit", "-qm", "fixture")
                return fingerprint("sample", root=root)

            git("init", "-q")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            previous = commit("books/sample/book.tex", "book")
            for path in ("docs/guide.md", "site/index.html", "books/other/book.tex"):
                self.assertEqual(commit(path, "unrelated"), previous)
            for path in (
                "books/sample/section.tex",
                "common/styles/shared.sty",
                "config/latexmkrc",
                "scripts/build_support.sh",
            ):
                current = commit(path, "build input")
                self.assertNotEqual(current, previous)
                previous = current
            git("mv", "books/sample/section.tex", "books/sample/renamed.tex")
            git("commit", "-qm", "rename")
            current = fingerprint("sample", root=root)
            self.assertNotEqual(current, previous)
            git("rm", "books/sample/renamed.tex")
            git("commit", "-qm", "delete")
            self.assertNotEqual(fingerprint("sample", root=root), current)

    def test_invalid_and_missing_books_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for book in ("../outside", "missing"):
                with self.subTest(book=book), self.assertRaises(ValueError):
                    fingerprint(book, root=Path(temporary))
