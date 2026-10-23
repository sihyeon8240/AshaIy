"""Extract balanced LaTeX sectioning titles and their plain-text fallbacks."""

from __future__ import annotations

import re

from scripts.latex_scan import braced_argument, command_arguments

TEXORPDFSTRING = re.compile(r"\\texorpdfstring\s*")


def tex_text(text: str) -> str:
    """Render plain registry text without granting it TeX command semantics."""
    escapes = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "$": r"\$",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(escapes.get(character, character) for character in text)


def chapter_titles(text: str) -> list[str]:
    return [item.argument for item in command_arguments(text, {"chapter"})]


def plain_text_title(title: str) -> str:
    """Replace each texorpdfstring with its recursively normalized PDF string."""
    output: list[str] = []
    position = 0
    while match := TEXORPDFSTRING.search(title, position):
        output.append(title[position : match.start()])
        _, after_tex = braced_argument(title, match.end())
        pdf, after_pdf = braced_argument(title, after_tex)
        output.append(plain_text_title(pdf))
        position = after_pdf
    output.append(title[position:])
    return "".join(output)
