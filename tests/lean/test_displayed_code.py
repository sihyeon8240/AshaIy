"""Linked display fragments preserve checked source and literal values."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.lean.displayed_code import check_file, normalized, regions

ROOT = Path(__file__).resolve().parents[2]


class DisplayedCodeTests(unittest.TestCase):
    def test_checked_fragments_allow_uniform_indentation_and_reject_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "lean/Textbooks/Sample/Topic/Result.lean"
            source.parent.mkdir(parents=True)
            source.write_text(
                "namespace Sample.Topic\n"
                "-- textbook:begin signature\n"
                "theorem result (n : Nat) : n + 0 = n\n"
                "-- textbook:end signature\n"
                ":= by\n"
                "-- textbook:begin proof\n"
                "  exact Nat.add_zero n\n"
                "-- textbook:end proof\n"
                "end Sample.Topic\n"
            )
            tex = root / "example.tex"
            tex.write_text(
                "% lean-source: lean/Textbooks/Sample/Topic/Result.lean#signature\n"
                "\\begin{lean}\n  theorem result (n : Nat) : n + 0 = n\n\\end{lean}\n"
                "% lean-source: lean/Textbooks/Sample/Topic/Result.lean#proof\n"
                "\\begin{lean}\n    exact Nat.add_zero n\n\\end{lean}\n"
            )
            self.assertEqual(check_file(tex, root, owner="Sample"), [])
            self.assertIn("owning textbook", check_file(tex, root, owner="Other")[0])
            if shutil.which("lake"):
                result = subprocess.run(
                    ["lake", "env", "lean", str(source)], cwd=ROOT / "lean", capture_output=True, text=True, timeout=60
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            tex.write_text(tex.read_text().replace("exact Nat.add_zero n", "exact Nat.zero_add n"))
            self.assertIn("differs", check_file(tex, root)[0])
            tex.write_text(tex.read_text().replace("#proof", "#missing"))
            self.assertIn("missing Lean fragment", check_file(tex, root)[0])

    def test_literals_fake_markers_and_malformed_regions_are_not_normalized_away(self):
        literal = 'def text := "first\n  second"'
        self.assertNotEqual(normalized(literal), normalized(literal.replace("  second", "second")))
        self.assertEqual(regions('def s := "-- textbook:begin fake"\n'), {})
        for text in (
            "-- textbook:begin first\n-- textbook:begin second\n",
            "-- textbook:end missing\n",
            "-- textbook:begin unfinished\n",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                regions(text)

    def test_annotations_inside_literal_tex_are_ignored_and_bad_links_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tex = root / "example.tex"
            tex.write_text("\\begin{verbatim}\n% lean-source: fake\n\\end{verbatim}\n")
            self.assertEqual(check_file(tex, root), [])
            tex.write_text("% lean-source: invalid\n\\begin{lean}\nexact h\n\\end{lean}\n")
            self.assertIn("malformed", check_file(tex, root)[0])
