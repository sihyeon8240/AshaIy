"""Check fonts and page breaks through the shared Lean code environment."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ("latexmk", "lualatex", "latexminted")
MISSING_TOOLS = [tool for tool in TOOLS if shutil.which(tool) is None]
if os.environ.get("REQUIRE_TEX_TESTS") == "1" and MISSING_TOOLS:
    raise RuntimeError("required rendering tools missing: " + ", ".join(MISSING_TOOLS))


@unittest.skipUnless(
    not MISSING_TOOLS,
    "Lean rendering checks require latexmk, lualatex, and latexminted",
)
class CodeFontTests(unittest.TestCase):
    def render(self, fixture: str, output: Path) -> Path:
        output.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["TEXINPUTS"] = os.pathsep.join(
            (
                str(ROOT / "common/styles"),
                str(ROOT / "tests/fixtures"),
                env.get("TEXINPUTS", ""),
                "",
            )
        )
        result = subprocess.run(
            [
                "latexmk",
                "-r",
                str(ROOT / "config/latexmkrc"),
                f"-outdir={output}",
                str(ROOT / "tests/fixtures" / f"{fixture}.tex"),
            ],
            cwd=output,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log = output / f"{fixture}.log"
        checked = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/latex/check_log.py"),
                "--strict",
                str(log),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertNotIn("LaTeX Font Warning:", log.read_text(encoding="utf-8"))
        self.assertTrue((output / f"{fixture}.pdf").read_bytes().startswith(b"%PDF-"))

        return output / f"{fixture}.aux"

    def test_shared_mathematics_and_bibliography_layout(self) -> None:
        output = ROOT / "build/mathematics-layout"
        output.mkdir(parents=True, exist_ok=True)
        (output / "mathematics-layout.bib").write_text(
            "@misc{layout,\n  title = {A typesetting test fixture},\n  year = {2026},\n}\n",
            encoding="utf-8",
        )
        self.render("mathematics-layout", output)

    def test_theorem_initial_lists_align_and_keep_prose_counters_and_qed(self) -> None:
        output = ROOT / "build/theorem-lists"
        aux = self.render("theorem-lists", output)
        positions = {
            name: (int(x), int(y), int(page))
            for name, x, y, page in re.findall(
                r"([a-z-]+):(\d+):(\d+):(\d+)", (output / "theorem-lists.positions").read_text()
            )
        }
        for kind in ("enum", "proof", "description", "later", "nested", "outside"):
            first = positions[f"{kind}-first"]
            second = positions[f"{kind}-second"]
            self.assertAlmostEqual(first[0], second[0], delta=100)
            self.assertEqual(first[2], second[2])
            self.assertGreater(first[1], second[1])
        for kind in ("enum", "proof", "description", "boundary"):
            heading = positions[f"{kind}-heading"]
            first = positions[f"{kind}-first"]
            self.assertEqual(heading[2], first[2], kind)
            self.assertGreater(heading[1], first[1], kind)
        self.assertEqual(positions["prose-heading"][1:], positions["prose-body"][1:])
        self.assertEqual(positions["qed"][2], positions["proof-second"][2])
        labels = dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}", aux.read_text()))
        self.assertEqual(labels["enum-definition"], "0.1.1")
        self.assertEqual(labels["shared-theorem"], "0.1.3")
        self.assertEqual(labels["independent-problem"], "0.1.1")
        self.assertEqual(labels["reset-theorem"], "0.2.1")

    def test_glyphs_in_regular_italic_bold_and_bold_italic(self) -> None:
        self.render("lean-fonts", ROOT / "build/font-check")

    def test_empty_sections_break_without_separating_heading_and_body(self) -> None:
        aux = self.render("empty-section-page-breaks", ROOT / "build/empty-section-page-breaks")
        pages = {
            name: int(page) for name, page in re.findall(r"\\newlabel\{([^}]+)\}\{\{[^}]*\}\{(\d+)\}", aux.read_text())
        }
        self.assertGreater(pages["body-heading"], pages["first-empty"])
        self.assertEqual(pages["body-heading"], pages["body-paragraph"])

    def test_short_boxes_stay_whole_and_long_boxes_split(self) -> None:
        aux = self.render("lean-page-breaks", ROOT / "build/lean-page-breaks")
        pages = {
            name: int(page) for name, page in re.findall(r"\\newlabel\{([^}]+)\}\{\{[^}]*\}\{(\d+)\}", aux.read_text())
        }
        for kind in ("short", "long"):
            self.assertGreater(pages[f"{kind}-start"], pages[f"before-{kind}"])

        for kind in ("short", "long", "display"):
            self.assertIn(
                pages[f"{kind}-start"],
                (pages[f"{kind}-prose"], pages[f"{kind}-prose"] + 1),
            )

        self.assertEqual(pages["short-start"], pages["short-end"])
        self.assertEqual(pages["long-start"], pages["long-sixth"])
        self.assertGreater(pages["long-end"], pages["long-start"] + 1)


if __name__ == "__main__":
    unittest.main()
