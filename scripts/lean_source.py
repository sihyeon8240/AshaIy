"""Ignore Lean comments and literals when checking source-level proof markers."""

from __future__ import annotations

import re


def ignored_spans(text: str) -> list[tuple[int, int, str]]:
    """Locate nested comments, ordinary/raw strings, and quoted identifiers."""
    spans: list[tuple[int, int, str]] = []
    position = 0
    while position < len(text):
        start = position
        if text.startswith("--", position):
            kind = "comment"
            end = text.find("\n", position)
            position = len(text) if end < 0 else end
        elif text.startswith("/-", position):
            kind = "comment"
            depth = 1
            position += 2
            while position < len(text) and depth:
                if text.startswith("/-", position):
                    depth += 1
                    position += 2
                elif text.startswith("-/", position):
                    depth -= 1
                    position += 2
                else:
                    position += 1
        elif raw := re.match(r'r(#+)?"', text[position:]):
            kind = "literal"
            closing = '"' + (raw.group(1) or "")
            end = text.find(closing, position + raw.end())
            position = len(text) if end < 0 else end + len(closing)
        elif text[position] in ('"', "«"):
            kind = "literal"
            closing = '"' if text[position] == '"' else "»"
            position += 1
            while position < len(text):
                char = text[position]
                position += 1
                if char == "\\" and closing == '"':
                    position += 1
                elif char == closing:
                    break
        else:
            position += 1
            continue
        spans.append((start, min(position, len(text)), kind))
    return spans


def without_comments_and_literals(text: str) -> str:
    """Preserve positions while masking comments and literals."""
    output = list(text)
    for start, end, _ in ignored_spans(text):
        for index in range(start, end):
            if output[index] not in "\r\n":
                output[index] = " "
    return "".join(output)


def imports(text: str) -> list[tuple[str, int]]:
    """Return module names and source lines, allowing whitespace after import."""
    clean = without_comments_and_literals(text)
    return [
        (match.group(1), text.count("\n", 0, match.start(1)) + 1)
        for match in re.finditer(
            r"(?m)^\s*(?:public\s+)?import\s+([A-Za-z_][A-Za-z0-9_.']*)", clean
        )
    ]


def escape_hatch_lines(text: str) -> list[int]:
    """Find unfinished proofs and axiom declarations, including anonymous examples."""
    clean = without_comments_and_literals(text)
    return [
        clean.count("\n", 0, match.start()) + 1
        for match in re.finditer(r"\b(?:sorry|admit|axiom)\b", clean)
    ]
