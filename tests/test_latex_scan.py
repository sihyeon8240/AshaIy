"""Tests for shared lightweight LaTeX scanning."""

from __future__ import annotations

import unittest

from scripts.latex_scan import command_arguments, theorem_label_groups, without_comments


class LatexScanTests(unittest.TestCase):
    def test_literal_examples_do_not_create_results_or_labels(self) -> None:
        fake = r"\begin{theorem}\label{fake}\end{theorem}"
        literals = [
            rf"\verb|{fake}%|",
            rf"\verb*+{fake}+",
            *[
                rf"\begin{{{name}}}" + "\n" + fake + "\n" + rf"\end{{{name}}}"
                for name in ("lean", "verbatim", "Verbatim", "minted", "lstlisting")
            ],
        ]
        text = (
            "\n".join(literals)
            + "\n"
            + (r"\begin{theorem}\label{real}\label{alias}x\end{theorem}")
        )
        self.assertEqual(theorem_label_groups(text), [{"real", "alias"}])
        self.assertEqual(
            [item.argument for item in command_arguments(text, {"label"})],
            ["real", "alias"],
        )

    def test_comments_and_escaped_percent_are_distinguished(self) -> None:
        text = "visible \\% text % hidden\nnext\n"
        clean = without_comments(text)
        self.assertIn(r"\%", clean)
        self.assertNotIn("hidden", clean)
        self.assertEqual(clean.count("\n"), text.count("\n"))

    def test_commands_allow_whitespace_and_balanced_arguments(self) -> None:
        text = "% \\label{ignored}\n\\label\n {outer-{inner}}\n"
        self.assertEqual(
            [item.argument for item in command_arguments(text, {"label"})],
            ["outer-{inner}"],
        )


if __name__ == "__main__":
    unittest.main()
