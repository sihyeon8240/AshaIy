"""Cleanup, environment inspection, and public Make usage."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

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
                ROOT / "scripts/clean_artifacts.sh",
                scripts / "clean_artifacts.sh",
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
                root / "__latexindent_temp_section.tex",
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
                [str(scripts / "clean_artifacts.sh")],
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

    def test_traversal_failure_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "config/generated").mkdir(parents=True)
            shutil.copy2(ROOT / "scripts/clean_artifacts.sh", root / "scripts")
            for name in ("cleanup-files.txt", "cleanup-prune.txt"):
                shutil.copy2(
                    ROOT / "config/generated" / name, root / "config/generated"
                )
            binary = root / "bin"
            binary.mkdir()
            find = binary / "find"
            find.write_text("#!/bin/sh\nexit 19\n")
            find.chmod(0o755)
            result = subprocess.run(
                [str(root / "scripts/clean_artifacts.sh")],
                env={**os.environ, "PATH": f"{binary}:{os.environ['PATH']}"},
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 19)


if __name__ == "__main__":
    unittest.main()
