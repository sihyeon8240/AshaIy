"""Cleanup, environment inspection, and public Make usage."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_support import write_executable

ROOT = Path(__file__).resolve().parent.parent


class CleanTests(unittest.TestCase):
    def test_clean_removes_make_and_vscode_build_contents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(ROOT / "scripts/clean.sh", scripts / "clean.sh")
            (root / "build/nested").mkdir(parents=True)
            (root / "build/nested/output.pdf").write_bytes(b"pdf")
            (root / "vscode-build/nested").mkdir(parents=True)
            (root / "vscode-build/nested/output.pdf").write_bytes(b"pdf")
            outside = root / "keep.txt"
            outside.write_text("keep", encoding="utf-8")

            result = subprocess.run(
                [str(scripts / "clean.sh")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list((root / "build").iterdir()), [])
            self.assertEqual(list((root / "vscode-build").iterdir()), [])
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep")


class CleanArtifactsTests(unittest.TestCase):
    def test_removes_artifacts_and_preserves_outputs_and_caches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cleanup paths ") as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(
                ROOT / "scripts/clean-artifacts.sh",
                scripts / "clean-artifacts.sh",
            )
            (root / "config/generated").mkdir(parents=True)
            for name in ("cleanup-files.txt", "cleanup-prune.txt"):
                shutil.copy2(
                    ROOT / "config/generated" / name, root / "config/generated" / name
                )

            artifacts = (
                root / "chapter.aux",
                root / "chapter.log",
                root / "chapter with spaces.pdf",
                root / "chapter\nname.aux",
                root / "change.patch.orig",
                root / "change.patch.rej",
                root / "notes.tex~",
                root / "notes.tex.bak",
                root / "notes.tex.swp",
                root / ".books.yml.interrupted.tmp",
            )
            for artifact in artifacts:
                artifact.write_text("discard", encoding="utf-8")

            preserved = (
                root / "build/tree.txt",
                root / "module.pyc",
                root / ".DS_Store",
                root / ".git/metadata.log",
                root / "nested/chapter.aux/keep.tex",
                root / "keep.tex",
                root / "build/book.log",
                root / "vscode-build/book.aux",
                root / ".cache/latexindent/indent.log",
                root / ".cache/mathlib/download.log",
                root / "lean/.lake/build.log",
            )
            for path in preserved:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("keep", encoding="utf-8")

            result = subprocess.run(
                [str(scripts / "clean-artifacts.sh")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(not artifact.exists() for artifact in artifacts))
            self.assertTrue(
                all(path.read_text(encoding="utf-8") == "keep" for path in preserved)
            )


class EnvironmentCheckTests(unittest.TestCase):
    def test_missing_repository_structure_is_reported_after_toolchain_check(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(ROOT / "scripts/check-environment.sh", scripts)
            write_executable(
                scripts / "check-toolchain.sh", "#!/usr/bin/env bash\nexit 0\n"
            )

            result = subprocess.run(
                [str(scripts / "check-environment.sh")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("scripts/ashaiy missing", result.stderr)


if __name__ == "__main__":
    unittest.main()
