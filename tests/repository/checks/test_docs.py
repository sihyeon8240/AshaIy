"""Regression checks for stale authoring guidance and broken local links."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.repository.checks import documentation_checks as docs

ROOT = Path(__file__).resolve().parents[3]


class DocumentationTests(unittest.TestCase):
    def test_links_detect_missing_paths_anchors_and_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# Target\n\n## Details\n")
            source = root / "README.md"
            source.write_text(
                "[ok](target.md#details)\n[bad](target.md#old)\n"
                "[`gone`](gone.md)\n[ref][missing]\n"
                "[valid][target]\n[target]: target.md#target\n"
                "[web](https://example.invalid)\n"
                "```md\n[example](absent.md)\n```\n"
                "`[example](absent.md)`\n"
            )
            errors = docs.link_errors(source, root)
            self.assertEqual(len(errors), 3, errors)
            self.assertIn("missing heading anchor: target.md#old", errors)
            self.assertIn("missing link target: gone.md", errors)
            self.assertIn("undefined link reference: missing", errors)

    def test_environment_check_detects_drift_in_both_directions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "common/styles").mkdir(parents=True)
            (root / "docs/writing-guide.md").write_text(
                "### Theorem environments\n\n"
                "The public environments are `theorem`, `exercise`, and `proof`. Use them.\n"
            )
            (root / "common/styles/theorems.sty").write_text(
                "\\RequirePackage{amsthm}\n"
                "\\newtheorem{theorem}{Theorem}\n"
                "\\newtheorem*{remark}{Remark}\n"
                "% \\newtheorem{exercise}{Exercise}\n"
            )
            self.assertEqual(
                docs.environment_errors(root),
                [
                    "documented environment is undefined: exercise",
                    "shared environment is undocumented: remark",
                ],
            )


if __name__ == "__main__":
    unittest.main()
