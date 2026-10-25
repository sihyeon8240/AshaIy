"""Math argument normalization and preservation of opaque TeX source."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.latex.normalize_braces import normalize_braces


class BraceNormalizationTests(unittest.TestCase):
    def test_math_arguments_follow_command_arity_and_field_syntax(self) -> None:
        examples = {
            r"\int_0^1 x^2": r"\int_{0}^{1} x^{2}",
            r"a_i + x^\alpha": r"a_{i} + x^{\alpha}",
            r"\frac12 + \frac1{n+1}": r"\frac{1}{2} + \frac{1}{n+1}",
            r"\frac\alpha n": r"\frac{\alpha}{n}",
            r"\sqrt x + \sqrt[3]x": r"\sqrt{x} + \sqrt[3]{x}",
            r"\sqrt\frac12": r"\sqrt{\frac{1}{2}}",
            r"\mathcal G_2 + \mathbf v": r"\mathcal{G}_{2} + \mathbf{v}",
            r"x_\mathrm{finite}": r"x_{\mathrm{finite}}",
            r"x^\frac12": r"x^{\frac{1}{2}}",
            r"x^{n^2}": r"x^{n^{2}}",
            r"\sin{x^2}": r"\sin{x^{2}}",
            r"\overset\alpha a": r"\overset{\alpha}{a}",
            r"\operatorname*{lim}_n": r"\operatorname*{lim}_{n}",
            r"\sqrt[a^2]{x_i}": r"\sqrt[a^{2}]{x_{i}}",
            r"x^+ + a_! + \frac-2": r"x^{+} + a_{!} + \frac{-}{2}",
            r"\frac {1} {n}": r"\frac {1} {n}",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                formatted = normalize_braces("$" + source + "$")
                self.assertEqual(formatted, "$" + expected + "$")
                self.assertEqual(normalize_braces(formatted), formatted)

    def test_math_delimiters_and_text_arguments_keep_their_context(self) -> None:
        examples = {
            r"\(x^2\) and \[a_i\]": r"\(x^{2}\) and \[a_{i}\]",
            r"$$x^2$$": r"$$x^{2}$$",
            r"\begin{align}x^2 &= a_i\end{align}": (
                r"\begin{align}x^{2} &= a_{i}\end{align}"
            ),
            r"\section*{Example $x^2$}": r"\section*{Example $x^{2}$}",
            r"\emph x": r"\emph{x}",
            r"\hbox to 10pt{$x^2$}": r"\hbox to 10pt{$x^{2}$}",
            r"\ensuremath{x^2}": r"\ensuremath{x^{2}}",
            r"$\text{file_name and $x^2$}$": r"$\text{file_name and $x^{2}$}$",
            r"\texorpdfstring{$\bm{x^2}$}{x²}": (r"\texorpdfstring{$\bm{x^{2}}$}{x²}"),
            "$x_ % keep comment\n  i$": "$x_ % keep comment\n  {i}$",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_braces(source), expected)
                self.assertEqual(normalize_braces(expected), expected)

    def test_literals_definitions_and_unknown_arguments_keep_their_bytes(self) -> None:
        examples = [
            "% $x^2$ and \\frac12\n",
            r"\verb|$x^2$ \frac12|",
            r"\verb*+$x^2$+",
            *[
                rf"\begin{{{name}}}" + "\n$x^2$ \\frac12\n" + rf"\end{{{name}}}"
                for name in ("lean", "verbatim", "Verbatim", "minted", "lstlisting")
            ],
            r"\newcommand{\power}[1]{$#1^2$}",
            r"\newcommand\power[1]{$#1^2$}",
            r"\DeclarePairedDelimiterXPP{\test}[1]{}{.}{\rvert}{^2}{$#1^2$}",
            r"\def\power#1^2{$#1^2$}",
            r"\directlua{print('$x^2$')}",
            r"$\custom{a_i}[x^2]$",
            r"$x_\custom{a_i}$",
            r"$\label{key_i} \url{https://example.org/a_b^2}$",
            r"\$x^2 and file_name",
            r"$x^^32$",
            r"$\frac1$",
            r"$x^{2$",
            r"$x_$",
        ]
        for source in examples:
            with self.subTest(source=source):
                self.assertEqual(normalize_braces(source), source)

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex is required")
    def test_normalized_formulas_preserve_tex_box_dimensions(self) -> None:
        examples = [
            r"\int_0^1 x^2\,dx",
            r"\frac12 + \frac\alpha n",
            r"\sqrt x + \sqrt[3]x + \sqrt\frac12",
            r"\mathcal G_2 + \mathbf v",
            r"x_\mathrm{finite} + x^\frac12",
            r"x^+ + a_! + \frac-2",
        ]
        lines = [
            r"\documentclass{article}",
            r"\usepackage{amsmath,amssymb}",
            r"\begin{document}",
        ]
        for index, source in enumerate(examples):
            formatted = normalize_braces("$" + source + "$")
            lines.extend(
                [
                    r"\setbox0=\hbox{$" + source + "$}",
                    r"\setbox1=\hbox{" + formatted + "}",
                    *[
                        rf"\ifdim\{dimension}0=\{dimension}1\else"
                        rf"\errmessage{{Changed formula {index}: {dimension}}}\fi"
                        for dimension in ("wd", "ht", "dp")
                    ],
                ]
            )
        lines.append(r"\end{document}")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "braces.tex"
            source.write_text("\n".join(lines) + "\n")
            result = subprocess.run(
                [
                    "lualatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    f"-output-directory={root}",
                    str(source),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
