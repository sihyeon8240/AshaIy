"""Shared lightweight scanning helpers for repository-owned LaTeX sources."""

from __future__ import annotations

import re
from dataclasses import dataclass


def is_escaped(text: str, position: int) -> bool:
    """Return whether the character at position has an odd backslash prefix."""
    backslashes = 0
    position -= 1
    while position >= 0 and text[position] == "\\":
        backslashes += 1
        position -= 1
    return backslashes % 2 == 1


LITERAL_ENVIRONMENTS = {"lean", "verbatim", "Verbatim", "minted", "lstlisting"}
SOURCE_TOKEN = re.compile(r"%|\\verb\*?(?![A-Za-z@])|\\begin\s*\{([^}]+)\}")


@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int
    kind: str


def source_spans(text: str) -> list[SourceSpan]:
    """Locate comments, inline verb/verb*, and literal environments in source order.

    Literal contents are opaque, including percent signs and apparent commands.
    An unfinished literal extends to EOF so checks never interpret its contents.
    """
    spans: list[SourceSpan] = []
    position = 0
    while match := SOURCE_TOKEN.search(text, position):
        position = match.end()
        if is_escaped(text, match.start()):
            continue
        if match.group() == "%":
            end = text.find("\n", position)
            end = len(text) if end < 0 else end
            kind = "comment"
        elif match.group().startswith(r"\verb"):
            if position == len(text) or text[position].isspace():
                continue
            end = text.find(text[position], position + 1)
            end = len(text) if end < 0 else end + 1
            kind = "verb"
        else:
            environment = match.group(1)
            if environment.rstrip("*") not in LITERAL_ENVIRONMENTS:
                continue
            closing = re.search(r"\\end\s*\{" + re.escape(environment) + r"\}", text[position:])
            end = len(text) if closing is None else position + closing.end()
            kind = environment
        spans.append(SourceSpan(match.start(), end, kind))
        position = end
    return spans


def masked_source(text: str, *, literals: bool) -> str:
    output = list(text)
    for span in source_spans(text):
        if span.kind == "comment" or literals:
            for position in range(span.start, span.end):
                if output[position] not in "\r\n":
                    output[position] = " "
    return "".join(output)


def without_comments(text: str) -> str:
    """Mask comments while preserving line and column positions."""
    return masked_source(text, literals=False)


def without_comments_and_literals(text: str) -> str:
    """Mask comments and supported literals while preserving source positions."""
    return masked_source(text, literals=True)


def braced_argument(text: str, start: int) -> tuple[str, int]:
    """Read one balanced braced argument starting at or after start."""
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != "{":
        raise ValueError("expected a braced LaTeX argument")
    depth = 1
    position = start + 1
    while position < len(text):
        character = text[position]
        if character == "{" and not is_escaped(text, position):
            depth += 1
        elif character == "}" and not is_escaped(text, position):
            depth -= 1
            if depth == 0:
                return text[start + 1 : position], position + 1
        position += 1
    raise ValueError("unterminated braced LaTeX argument")


def has_balanced_braces(text: str) -> bool:
    """Return whether text can safely be embedded in one braced argument."""
    wrapped = "{" + text + "}"
    try:
        _, end = braced_argument(wrapped, 0)
    except ValueError:
        return False
    return end == len(wrapped)


@dataclass(frozen=True)
class CommandArgument:
    name: str
    argument: str
    position: int


def command_arguments(text: str, names: set[str]) -> list[CommandArgument]:
    """Return required braced arguments outside comments and literals."""
    if not names:
        return []
    clean = without_comments_and_literals(text)
    pattern = re.compile(
        r"\\(?P<name>" + "|".join(re.escape(name) for name in sorted(names)) + r")"
        r"(?![A-Za-z@])\*?"
    )
    found: list[CommandArgument] = []
    for match in pattern.finditer(clean):
        if is_escaped(clean, match.start()):
            continue
        try:
            argument, _ = braced_argument(clean, match.end())
        except ValueError:
            continue
        found.append(CommandArgument(match.group("name"), argument, match.start()))
    return found


def theorem_label_groups(text: str) -> list[set[str]]:
    """Return one label set per result environment, including unlabeled results."""
    stack: list[tuple[str, set[str] | None]] = []
    results = {"theorem", "lemma", "proposition", "corollary"}
    groups: list[set[str]] = []
    for command in command_arguments(text, {"begin", "end", "label"}):
        if command.name == "begin":
            labels = set() if command.argument in results else None
            if labels is not None:
                groups.append(labels)
            stack.append((command.argument, labels))
        elif command.name == "end":
            if stack and stack[-1][0] == command.argument:
                stack.pop()
        elif stack and stack[-1][1] is not None:
            stack[-1][1].add(command.argument)
    return groups
