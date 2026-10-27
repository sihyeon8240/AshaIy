"""Book caches reuse unrelated commits and invalidate changed build inputs."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.ci.book_cache import describe_inputs, fingerprint
from tests.support.fixtures import (
    book_record,
    copy_script,
    git_environment,
    manifest_document,
    write_yaml,
)


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
                "scripts/latex/build_support.sh",
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

    def test_registry_projection_is_book_owned_and_committed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*arguments: str) -> None:
                subprocess.run(
                    ["git", *arguments],
                    cwd=root,
                    env=git_environment(),
                    check=True,
                    capture_output=True,
                )

            def commit() -> dict[str, str]:
                git("add", ".")
                git("commit", "-qm", "fixture")
                return {
                    slug: fingerprint(slug, root=root) for slug in ("alpha", "beta")
                }

            git("init", "-q")
            for slug in ("alpha", "beta"):
                entry = root / "books" / slug / "book.tex"
                entry.parent.mkdir(parents=True)
                entry.write_text(f"Publication metadata for {slug}\n")
            registry = root / "config/books.yml"
            registry.parent.mkdir()
            document = manifest_document(
                [book_record("alpha"), book_record("beta", order=20)]
            )
            write_yaml(registry, document)
            before = commit()
            document["books"][0]["order"] = 30
            write_yaml(registry, document)
            self.assertEqual(commit(), before)
            document["books"][0]["title"] = "Revised Alpha"
            write_yaml(registry, document)
            (root / "books/alpha/book.tex").write_text(
                "Revised alpha publication metadata\n"
            )
            after = commit()
            self.assertNotEqual(before["alpha"], after["alpha"])
            self.assertEqual(before["beta"], after["beta"])
            (root / "books/alpha/book.tex").write_text("Uncommitted edit\n")
            registry.write_text("Uncommitted registry edit\n")
            self.assertEqual(fingerprint("alpha", root=root), after["alpha"])
            self.assertEqual(
                describe_inputs("alpha", root=root).metadata_source,
                "books/alpha/book.tex",
            )

    def test_input_description_bootstraps_without_third_party_packages(self) -> None:
        import json
        import sys

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            copy_script(
                Path(__file__).resolve().parents[2] / "scripts/ci/book_cache.py",
                scripts / "ci/book_cache.py",
            )
            entry = root / "books/sample/book.tex"
            entry.parent.mkdir(parents=True)
            entry.write_text("Publication metadata\n")
            for arguments in (
                ("init", "-q"),
                ("add", "."),
                ("commit", "-qm", "fixture"),
            ):
                subprocess.run(
                    ["git", *arguments],
                    cwd=root,
                    env=git_environment(),
                    check=True,
                    capture_output=True,
                )
            result = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    str(scripts / "ci/book_cache.py"),
                    "sample",
                    "--format",
                    "json",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(
                json.loads(result.stdout)["fingerprint"],
                fingerprint("sample", root=root),
            )
