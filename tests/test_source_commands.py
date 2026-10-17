"""Repository source checks and end-of-file normalization."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_support import write_executable

ROOT = Path(__file__).resolve().parent.parent


class FocusedCheckCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(
            ROOT / "scripts",
            self.root / "scripts",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        for name in (
            "config/authoring.json",
            "config/authoring.json",
            "config/authoring.json",
            "scripts/repository_cli.py",
            "scripts/repository_tasks.py",
            "scripts/task_stages.py",
            "scripts/source_reads.py",
        ):
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        for name in ("books.py", "check-proof-links.py", "check-docs.py"):
            (self.root / "scripts" / name).write_text(
                "import os\nimport sys\nfrom pathlib import Path\nPath('called').write_text(Path(__file__).name + ' ' + ' '.join(sys.argv[1:]))\nraise SystemExit(int(os.environ['CHECK_STATUS']))\n"
            )
        write_executable(
            self.root / "scripts/check-repository.sh",
            "#!/usr/bin/env bash\nprintf 'check-repository.sh ' > called\nexit \"$CHECK_STATUS\"\n",
        )

    def run_check(self, entry: str, *arguments: str, status: int = 0):
        command = [sys.executable, "scripts/repository_cli.py", "check"]
        return subprocess.run(
            [*command, *arguments],
            cwd=self.root,
            env={**os.environ, "PYTHON": sys.executable, "CHECK_STATUS": str(status)},
            text=True,
            capture_output=True,
            timeout=15,
        )

    def test_focused_checks_preserve_selection_and_failure_status(self) -> None:
        scopes = {
            "source": "check-repository.sh ",
            "manifest": "books.py validate",
            "proof-links": "check-proof-links.py ",
            "docs": "check-docs.py ",
        }
        for entry in ("python",):
            for scope, expected in scopes.items():
                for status in (0, 7):
                    with self.subTest(entry=entry, scope=scope, status=status):
                        result = self.run_check(entry, scope, status=status)
                        expected_status = 2 if False and status else status
                        self.assertEqual(
                            result.returncode, expected_status, result.stderr
                        )
                        self.assertEqual((self.root / "called").read_text(), expected)

    def test_invalid_requests_do_not_start_checks(self) -> None:
        for entry in ("python",):
            strict = "--strict"
            requests = [(), ("unknown",), ("docs", "manifest")]
            requests.extend(
                (
                    (scope, strict)
                    for scope in ("source", "manifest", "proof-links", "docs")
                )
            )
            for arguments in requests:
                with self.subTest(entry=entry, arguments=arguments):
                    result = self.run_check(entry, *arguments)
                    self.assertEqual(result.returncode, 2)
                    self.assertFalse((self.root / "called").exists())


class RepositorySourceCheckTests(unittest.TestCase):
    def test_syntax_error_in_later_script_stops_source_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir(exist_ok=True)
            shutil.copy2(ROOT / "scripts/check-repository.sh", scripts)
            (scripts / "aaa-valid.sh").write_text("exit 0\n", encoding="utf-8")
            (scripts / "zzz-invalid.sh").write_text("if then\n", encoding="utf-8")
            binary = root / "bin"
            binary.mkdir()
            for name in ("rg", "shellcheck"):
                command = binary / name
                write_executable(command, "#!/bin/sh\nexit 0\n")
            result = subprocess.run(
                [str(scripts / "check-repository.sh")],
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
            self.assertNotIn("books.py", result.stderr)


class NormalizeEofTests(unittest.TestCase):
    def test_format_condenses_consecutive_blank_lines_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "multiple-blank-lines.tex"
            path.write_bytes(b"first\n\n\nsecond\n")
            result = subprocess.run(
                [
                    str(ROOT / "scripts/normalize-eof.sh"),
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
                [str(ROOT / "scripts/normalize-eof.sh"), *map(str, paths)],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all((path.read_bytes() == b"content\n" for path in paths)))

    def test_check_rejects_missing_or_extra_final_lf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            valid = Path(directory) / "valid.tex"
            missing = Path(directory) / "missing.tex"
            extra = Path(directory) / "extra.tex"
            valid.write_bytes(b"content\n")
            missing.write_bytes(b"content")
            extra.write_bytes(b"content\n\n")
            valid_result = subprocess.run(
                [str(ROOT / "scripts/normalize-eof.sh"), "--check", str(valid)],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            invalid_result = subprocess.run(
                [
                    str(ROOT / "scripts/normalize-eof.sh"),
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
            command = [str(ROOT / "scripts/normalize-eof.sh"), "--check"]
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
                [str(ROOT / "scripts/normalize-eof.sh")],
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
