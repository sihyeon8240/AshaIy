"""Book-root presentation files take precedence over shared templates."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FrontmatterTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("lualatex"), "lualatex is required")
    def test_local_frontmatter_and_shared_fallback_use_the_same_entry_point(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            book = root / "book"
            templates = root / "common/templates"
            chapter = book / "chapters/introduction"
            chapter.mkdir(parents=True)
            templates.mkdir(parents=True)
            (chapter / "index.tex").write_text("Body.\n")
            shutil.copyfile(ROOT / "common/templates/book.tex", book / "book.tex")
            (book / "textbook.sty").write_text(
                "\\ProvidesPackage{textbook}\n\\newcommand{\\addbibresource}[1]{}\n\\newcommand{\\printbibliography}{}\n"
            )
            for name in ("cover", "preface"):
                (templates / f"{name}.tex").write_text(rf"\typeout{{FRONTMATTER-{name}-shared}}" + "\n")
            for local in (False, True):
                with self.subTest(local=local):
                    if local:
                        for name in ("cover", "preface"):
                            (book / f"{name}.tex").write_text(rf"\typeout{{FRONTMATTER-{name}-local}}" + "\n")
                    result = subprocess.run(
                        [
                            "lualatex",
                            "-interaction=nonstopmode",
                            "-halt-on-error",
                            "book.tex",
                        ],
                        cwd=book,
                        env={**os.environ, "TEXINPUTS": f".:{templates}//:"},
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    expected, absent = ("local", "shared") if local else ("shared", "local")
                    for name in ("cover", "preface"):
                        self.assertIn(f"FRONTMATTER-{name}-{expected}", result.stdout)
                        self.assertNotIn(f"FRONTMATTER-{name}-{absent}", result.stdout)
