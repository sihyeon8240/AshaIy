"""Public CLI parsing, checkout discovery, and selection boundaries."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.cli.repository_cli import build_parser, main
from tests.support.fixtures import (
    book_record,
    copy_file,
    copy_validation_configuration,
    manifest_document,
    write_yaml,
)

ROOT = Path(__file__).resolve().parents[2]


class AshaiyTests(unittest.TestCase):
    def test_all_book_options_resolve_slugs_and_label_prefixes(self):
        commands = (
            ["book", "build"],
            ["book", "release", "--version", "0.2.0"],
            ["contents", "check"],
            ["contents", "generate"],
            ["generated", "check"],
            ["generated", "generate"],
            ["site", "check"],
            ["site", "generate"],
            ["doctor", "book"],
        )
        for command in commands:
            for selector in ("linear-algebra", "la", "linear"):
                with self.subTest(command=command, selector=selector):
                    args = build_parser().parse_args([*command, "--book", selector])
                    self.assertEqual(args.book, "linear-algebra")

    def test_ambiguous_unknown_and_exact_selectors(self):
        books = [
            book_record("linear-algebra", label_prefix="la"),
            book_record("linear-analysis", label_prefix="lan"),
        ]
        with patch(
            "scripts.books.book_manifest.load_manifest", return_value={"books": books}
        ):
            parser = build_parser()
            for selector in ("lin", "missing", ""):
                with (
                    self.subTest(selector=selector),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    with self.assertRaises(SystemExit) as error:
                        parser.parse_args(["book", "build", "--book", selector])
                    self.assertEqual(error.exception.code, 2)
            self.assertEqual(
                parser.parse_args(["book", "build", "--book", "linear-algebra"]).book,
                "linear-algebra",
            )
            self.assertEqual(
                parser.parse_args(["book", "build", "--book", "la"]).book,
                "linear-algebra",
            )

    def test_invalid_combinations_do_not_dispatch_operations(self):
        cases = (
            ["book"],
            ["book", "release", "--version", "1.0.0"],
            ["book", "build", "--jobs", "0"],
            ["site", "build", "--book", "la"],
            ["format", "tex", "check"],
            ["config", "generate", "check"],
            ["clean", "cache"],
            ["check", "all", "--strict", "test"],
        )
        with patch("scripts.cli.repository_commands.execute") as execute:
            for command in cases:
                with (
                    self.subTest(command=command),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    with self.assertRaises(SystemExit) as error:
                        main(command)
                    self.assertEqual(error.exception.code, 2)
            execute.assert_not_called()

    def test_path_entry_point_works_from_subdirectory_and_preserves_file_paths(self):
        with tempfile.TemporaryDirectory(prefix="ashaiy checkout ") as directory:
            root = Path(directory)
            shutil.copytree(
                ROOT / "scripts",
                root / "scripts",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            copy_validation_configuration(root)
            binary = root / "bin/ashaiy"
            binary.parent.mkdir()
            copy_file(ROOT / "scripts/ashaiy_launcher.sh", binary)
            write_yaml(
                root / "config/books.yml",
                manifest_document([book_record("sample", label_prefix="s")]),
            )
            book = root / "books/sample"
            book.mkdir(parents=True)
            (book / "book.tex").write_text("Fixture.\n")
            (root / "scripts/repository/formatting/format_code.py").write_text(
                "import sys\nfrom pathlib import Path\n"
                'Path("captured").write_text(sys.argv[-1])\n'
            )
            environment = {
                **os.environ,
                "ASHAIY_ROOT": str(root),
                "PATH": f"{binary.parent}:{os.environ['PATH']}",
            }
            result = subprocess.run(
                ["ashaiy", "book", "list", "--format", "json"],
                cwd=book,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)[0]["slug"], "sample")
            result = subprocess.run(
                ["ashaiy", "format", "py", "--file", "draft space.py"],
                cwd=book,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (root / "captured").read_text(), str(book / "draft space.py")
            )

    def test_image_launcher_dispatches_to_the_selected_checkout(self):
        with tempfile.TemporaryDirectory(prefix="image launcher ") as directory:
            binary = Path(directory) / "ashaiy"
            copy_file(ROOT / "scripts/ashaiy_launcher.sh", binary)
            result = subprocess.run(
                [str(binary), "book", "list", "--format", "json"],
                cwd=directory,
                env={**os.environ, "ASHAIY_ROOT": str(ROOT)},
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "linear-algebra", [book["slug"] for book in json.loads(result.stdout)]
            )
