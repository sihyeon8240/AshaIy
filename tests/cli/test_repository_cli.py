"""Behavioral compatibility of the migrated contents command entry points."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support.fixtures import (
    book_record,
    copy_validation_configuration,
    manifest_document,
    write_yaml,
)

ROOT = Path(__file__).resolve().parents[2]


class ContentsCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(
            ROOT / "scripts",
            self.root / "scripts",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        copy_validation_configuration(self.root)
        shutil.copytree(ROOT / "common/templates", self.root / "common/templates")
        (self.root / "common/styles").mkdir()
        shutil.copyfile(
            ROOT / "common/styles/macros.yml", self.root / "common/styles/macros.yml"
        )
        shutil.copytree(ROOT / "config/generated", self.root / "config/generated")
        write_yaml(
            self.root / "config/books.yml",
            manifest_document(
                [book_record(slug, label_prefix=slug) for slug in ("first", "second")]
            ),
        )
        for slug in ("first", "second"):
            book = self.root / "books" / slug
            write_yaml(
                book / "chapters.yml",
                {
                    "schema_version": 1,
                    "chapters": [{"slug": "start", "title": "Start"}],
                },
            )
            chapter = book / "chapters/start"
            write_yaml(
                chapter / "sections.yml",
                {
                    "schema_version": 1,
                    "sections": [{"slug": "topic", "title": "Topic"}],
                },
            )
            (book / "book.tex").write_text("stale assembly\n")
            (chapter / "topic.tex").write_text("Body.\n")

    def book_sources(self) -> dict[Path, bytes]:
        return {
            path: path.read_bytes()
            for path in (self.root / "books").rglob("*")
            if path.is_file()
        }

    def run_command(self, entry, scope, *options):
        arguments = [sys.executable, f"scripts/{entry}"]
        if entry == "cli/repository_cli.py":
            check = "--check" in options
            options = [option for option in options if option != "--check"]
            arguments += ["contents", "check" if check else "generate"]
            if scope in {"all", "chap", "sec"}:
                arguments += [
                    "--scope",
                    {"chap": "chapters", "sec": "sections", "all": "all"}[scope],
                ]
            else:
                arguments += [scope]
        else:
            arguments += [scope]
        return subprocess.run(
            [*arguments, *options],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_generation_check_and_book_selection_across_entry_points(self) -> None:
        for entry in ("books/contents_generation.py", "cli/repository_cli.py"):
            with self.subTest(entry=entry):
                options = ["--book", "first"]
                book = self.root / "books/first"
                assembly = book / "book.tex"
                assembly.write_text("stale assembly\n")
                before = self.book_sources()
                checked = self.run_command(entry, "all", *options, *["--check"])
                self.assertEqual(checked.returncode, 1)
                self.assertIn("generated contents are stale", checked.stderr)
                self.assertEqual(before, self.book_sources())
                generated = self.run_command(entry, "all", *options)
                self.assertEqual(generated.returncode, 0, generated.stderr)
                self.assertIn("\\include{chapters/start/index}", assembly.read_text())
                self.assertEqual(
                    (self.root / "books/second/book.tex").read_text(),
                    "stale assembly\n",
                )
                checked = self.run_command(entry, "all", *options, *["--check"])
                self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_invalid_arguments_and_unknown_books_fail_without_writing(self) -> None:
        for entry in ("books/contents_generation.py", "cli/repository_cli.py"):
            for scope, selection in (("all", "absent"), ("invalid", "first")):
                with self.subTest(entry=entry, scope=scope, selection=selection):
                    options = ["--book", selection]
                    before = self.book_sources()
                    result = self.run_command(entry, scope, *options)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(before, self.book_sources())
                    if scope == "all":
                        self.assertIn("absent", result.stderr)

    def test_scopes_do_not_rewrite_other_assembly(self) -> None:
        for entry in ("books/contents_generation.py", "cli/repository_cli.py"):
            with self.subTest(entry=entry):
                options = ["--book", "first"]
                book = self.root / "books/first"
                assembly = book / "book.tex"
                index = book / "chapters/start/index.tex"
                assembly.write_text("preserve book\n")
                result = self.run_command(entry, "sec", *options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(assembly.read_text(), "preserve book\n")
                self.assertIn("\\section{Topic}", index.read_text())
                index.write_text("preserve index\n")
                result = self.run_command(entry, "chap", *options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(index.read_text(), "preserve index\n")
                self.assertIn("\\include{chapters/start/index}", assembly.read_text())

    def test_no_book_selection_generates_both_books(self) -> None:
        for entry in ("books/contents_generation.py", "cli/repository_cli.py"):
            with self.subTest(entry=entry):
                for slug in ("first", "second"):
                    (self.root / "books" / slug / "book.tex").write_text("stale\n")
                result = self.run_command(entry, "all")
                self.assertEqual(result.returncode, 0, result.stderr)
                for slug in ("first", "second"):
                    self.assertIn(
                        "\\include{chapters/start/index}",
                        (self.root / "books" / slug / "book.tex").read_text(),
                    )

    def test_integrated_generation_preserves_selection_and_check_mode(self) -> None:
        for entry in ("python",):
            with self.subTest(entry=entry):
                arguments = [
                    sys.executable,
                    "scripts/cli/repository_cli.py",
                    "generated",
                    "generate",
                    "--book",
                    "first",
                ]
                assembly = self.root / "books/first/book.tex"
                assembly.write_text("stale assembly\n")
                checked_arguments = [
                    value if value != "generate" else "check" for value in arguments
                ]
                before = self.book_sources()
                checked = subprocess.run(
                    checked_arguments,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertNotEqual(checked.returncode, 0)
                self.assertEqual(before, self.book_sources())
                generated = subprocess.run(
                    arguments, cwd=self.root, capture_output=True, text=True, timeout=15
                )
                self.assertEqual(generated.returncode, 0, generated.stderr)
                self.assertIn(
                    "Skipped site generation for disabled book: first", generated.stdout
                )
                self.assertTrue((self.root / "lean/Textbooks.lean").is_file())
                self.assertEqual(
                    (self.root / "books/second/book.tex").read_text(),
                    "stale assembly\n",
                )
                checked = subprocess.run(
                    checked_arguments,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(checked.returncode, 0, checked.stderr)


if __name__ == "__main__":
    unittest.main()
