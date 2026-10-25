"""Repository source checks and end-of-file normalization."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.repository.checks import source_checks
from tests.support.fixtures import copy_file, write_executable

ROOT = Path(__file__).resolve().parents[3]


class RepositorySourceCheckTests(unittest.TestCase):
    def test_generated_site_pages_and_tool_outputs_cannot_be_tracked(self) -> None:
        for name in (
            "site/books/sample.html",
            "site/_data/books.json",
            ".hypothesis/examples/cache",
            "tree.txt",
            "__latexindent_temp_book.tex",
        ):
            with (
                self.subTest(name=name),
                patch.object(source_checks.py_compile, "compile"),
                patch.object(
                    source_checks.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0),
                ),
                patch.object(
                    source_checks.subprocess,
                    "check_output",
                    return_value=name.encode() + b"\0",
                ),
                self.assertRaisesRegex(ValueError, "generated files are tracked"),
            ):
                source_checks.check_repository_files()

    def test_syntax_error_in_later_script_stops_source_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir(exist_ok=True)
            copy_file(ROOT / "scripts/repository/checks/check_repository.sh", scripts)
            (scripts / "aaa-valid.sh").write_text("exit 0\n", encoding="utf-8")
            (scripts / "zzz-invalid.sh").write_text("if then\n", encoding="utf-8")
            binary = root / "bin"
            binary.mkdir()
            for name in ("rg", "shellcheck"):
                command = binary / name
                write_executable(command, "#!/bin/sh\nexit 0\n")
            result = subprocess.run(
                [str(scripts / "repository/checks/check_repository.sh")],
                cwd=root,
                env={**os.environ, "PATH": f"{binary}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("zzz-invalid.sh", result.stderr)
            self.assertIn("syntax error", result.stderr)
            self.assertNotIn("books/books.py", result.stderr)


class NormalizeEofTests(unittest.TestCase):
    def test_format_condenses_consecutive_blank_lines_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "multiple-blank-lines.tex"
            path.write_bytes(b"first\n\n\nsecond\n")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/repository/formatting/normalize_eof.py"),
                    "--collapse-blank-lines",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_bytes(), b"first\n\nsecond\n")

    def test_format_adds_one_lf_and_removes_trailing_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = [
                Path(directory) / "missing-newline.tex",
                Path(directory) / "trailing-blank-lines.tex",
            ]
            paths[0].write_bytes(b"content")
            paths[1].write_bytes(b"content\n\n\n")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/repository/formatting/normalize_eof.py"),
                    *map(str, paths),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(path.read_bytes() == b"content\n" for path in paths))

    def test_explicit_files_preserve_bytes_line_endings_and_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.dat"
            path.write_bytes(b"\xff\x00first\r\nsecond\r\n\t ")
            path.chmod(0o640)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/repository/formatting/normalize_eof.py"),
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_bytes(), b"\xff\x00first\r\nsecond\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_check_rejects_missing_or_extra_final_lf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            valid = Path(directory) / "valid.tex"
            missing = Path(directory) / "missing.tex"
            extra = Path(directory) / "extra.tex"
            valid.write_bytes(b"content\n")
            missing.write_bytes(b"content")
            extra.write_bytes(b"content\n\n")
            valid_result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/repository/formatting/normalize_eof.py"),
                    "--check",
                    str(valid),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            invalid_result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/repository/formatting/normalize_eof.py"),
                    "--check",
                    str(missing),
                    str(extra),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(valid_result.returncode, 0, valid_result.stderr)
            self.assertEqual(invalid_result.returncode, 1)
            self.assertIn(str(missing), invalid_result.stderr)
            self.assertIn(str(extra), invalid_result.stderr)

    def test_full_check_excludes_only_paths_covered_by_formatters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
            covered = [
                "scripts/helper.py",
                "tests/test_sample.py",
                "scripts/build.sh",
                "books/sample/book.tex",
                "common/styles/sample.sty",
            ]
            remaining = ["README.md", "lean/Sample.lean", "other/helper.py"]
            for name in covered + remaining:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"missing newline")
            subprocess.run(["git", "add", "."], cwd=root, check=True, timeout=30)
            command = [
                sys.executable,
                str(ROOT / "scripts/repository/formatting/normalize_eof.py"),
                "--check",
            ]
            result = subprocess.run(
                [*command, "--exclude-formatted"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 1)
            for name in covered:
                self.assertNotIn(name, result.stderr)
            for name in remaining:
                self.assertIn(name, result.stderr)
            standalone = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(standalone.returncode, 1)
            for name in covered + remaining:
                self.assertIn(name, standalone.stderr)

    def test_without_paths_processes_tracked_text_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
            tracked = root / "tracked.txt"
            untracked = root / "untracked.txt"
            binary = root / "binary.dat"
            tracked.write_bytes(b"tracked")
            untracked.write_bytes(b"untracked")
            binary.write_bytes(b"binary\x00data")
            subprocess.run(
                ["git", "add", "tracked.txt", "binary.dat"],
                cwd=root,
                check=True,
                timeout=30,
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/repository/formatting/normalize_eof.py"),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(tracked.read_bytes(), b"tracked\n")
            self.assertEqual(untracked.read_bytes(), b"untracked")
            self.assertEqual(binary.read_bytes(), b"binary\x00data")


if __name__ == "__main__":
    unittest.main()
