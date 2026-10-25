"""Brace known LaTeX arguments without expanding user-defined commands."""

from __future__ import annotations

import re
from collections.abc import Mapping

from scripts.latex.command_specs import BUILTIN_COMMANDS, CommandSpec
from scripts.latex.latex_scan import source_spans

COMMAND = re.compile(r"\\([A-Za-z@]+|[^\r\n])")
MATH_ENVIRONMENTS = frozenset(
    "math displaymath equation equation* align align* alignat alignat* aligned "
    "alignedat gather gather* gathered multline multline* split eqnarray eqnarray* "
    "cases matrix pmatrix bmatrix Bmatrix vmatrix Vmatrix smallmatrix".split()
)
DEFINITION_COMMANDS = frozenset(
    "newcommand renewcommand providecommand DeclareRobustCommand NewDocumentCommand "
    "RenewDocumentCommand ProvideDocumentCommand DeclareDocumentCommand "
    "DeclareMathOperator DeclarePairedDelimiter DeclarePairedDelimiterX DeclarePairedDelimiterXPP "
    "newenvironment renewenvironment".split()
)


class BraceNormalizer:
    def __init__(self, source: str, commands: Mapping[str, CommandSpec]) -> None:
        self.source = source
        self.commands = commands
        self.protected = {span.start: span for span in source_spans(source)}

    def layout_end(self, position: int, end: int) -> int:
        while position < end:
            span = self.protected.get(position)
            if span is not None and span.kind == "comment":
                position = span.end
            elif self.source[position].isspace():
                position += 1
            else:
                break
        return position

    def group_end(self, position: int, end: int) -> int | None:
        opening = self.source[position]
        closing = "}" if opening == "{" else "]"
        depth = 1
        position += 1
        while position < end:
            span = self.protected.get(position)
            command = COMMAND.match(self.source, position, end)
            if span is not None:
                position = span.end
                continue
            if command is not None:
                position = command.end()
                continue
            character = self.source[position]
            if opening == "[" and character == "{":
                nested_end = self.group_end(position, end)
                if nested_end is None:
                    return None
                position = nested_end
                continue
            if character == opening:
                depth += 1
            elif character == closing:
                depth -= 1
                if depth == 0:
                    return position + 1
            position += 1
        return None

    def opaque_arguments_end(self, position: int, end: int) -> int:
        if position < end and self.source[position] == "*":
            position += 1
        while True:
            start = self.layout_end(position, end)
            if start == end or self.source[start] not in "[{":
                return position
            next_position = self.group_end(start, end)
            if next_position is None:
                return end
            position = next_position

    def argument(
        self,
        position: int,
        end: int,
        *,
        math: bool,
        field: bool = False,
        opaque: bool = False,
    ) -> tuple[str, int] | None:
        start = self.layout_end(position, end)
        if start == end or start in self.protected:
            return None
        prefix = self.source[position:start]
        character = self.source[start]
        if character == "{":
            next_position = self.group_end(start, end)
            if next_position is None:
                return None
            body = (
                self.source[start + 1 : next_position - 1]
                if opaque
                else self.normalize(start + 1, next_position - 1, math=math)
            )
        elif character.isalnum() or character in "+-=.,:;!?()[]/|<>":
            body = character
            next_position = start + 1
        elif command := COMMAND.match(self.source, start, end):
            name = command[1]
            spec = self.commands.get(name)
            if not field:
                body = command[0]
                next_position = command.end()
            elif spec is not None and spec.script_atom:
                parsed = self.command(command, end, math=math)
                if parsed is None:
                    return None
                body, next_position = parsed
            else:
                return None
        else:
            return None
        if character != "{" and not any(
            marker in prefix for marker in ("\n", "\r", "%")
        ):
            prefix = ""
        return prefix + "{" + body + "}", next_position

    def definition_end(self, position: int, end: int) -> int:
        while position < end:
            span = self.protected.get(position)
            command = COMMAND.match(self.source, position, end)
            if span is not None:
                position = span.end
            elif command is not None:
                position = command.end()
            elif self.source[position] == "{":
                return self.group_end(position, end) or end
            else:
                position += 1
        return end

    def command(
        self, match: re.Match[str], end: int, *, math: bool
    ) -> tuple[str, int] | None:
        name = match[1]
        spec = self.commands.get(name)
        if (
            spec is None
            or (spec.context == "math" and not math)
            or (spec.context == "text" and math)
        ):
            return None
        output = match[0]
        position = match.end()
        starred = False
        for argument_spec in spec.arguments:
            start = self.layout_end(position, end)
            if argument_spec.kind == "star":
                if self.source[start : start + 1] == "*":
                    output += self.source[position : start + 1]
                    position = start + 1
                    starred = True
                continue
            if argument_spec.kind == "optional":
                if self.source[start : start + 1] != "[":
                    continue
                if spec.paired and starred:
                    return None
                next_position = self.group_end(start, end)
                if next_position is None:
                    return None
                output += self.source[position : start + 1]
                output += (
                    self.source[start + 1 : next_position - 1]
                    if argument_spec.mode == "opaque"
                    else self.normalize(
                        start + 1, next_position - 1, math=argument_spec.mode == "math"
                    )
                )
                output += "]"
                position = next_position
                continue
            parsed = self.argument(
                position,
                end,
                math=argument_spec.mode == "math",
                field=argument_spec.field,
                opaque=argument_spec.mode == "opaque",
            )
            if parsed is None:
                return None
            argument, position = parsed
            output += argument
        return output, position

    def declaration_end(self, position: int, end: int) -> int:
        position = self.layout_end(position, end)
        if self.source[position : position + 1] == "*":
            position = self.layout_end(position + 1, end)
        if command := COMMAND.match(self.source, position, end):
            position = command.end()
        return self.opaque_arguments_end(position, end)

    def normalize(self, start: int, end: int, *, math: bool = False) -> str:
        output: list[str] = []
        environments: list[tuple[str, bool]] = []
        position = start
        while position < end:
            span = self.protected.get(position)
            if span is not None:
                output.append(self.source[position : span.end])
                position = span.end
                continue
            character = self.source[position]
            command = COMMAND.match(self.source, position, end)
            if command is not None:
                name = command[1]
                next_position = command.end()
                argument_start = self.layout_end(next_position, end)
                if name in {"def", "gdef", "edef", "xdef"}:
                    # A definition's parameter delimiters are syntax, not math fields.
                    next_position = self.definition_end(next_position, end)
                elif name in DEFINITION_COMMANDS:
                    next_position = self.declaration_end(next_position, end)
                elif (
                    name in {"begin", "end"}
                    and self.source[argument_start : argument_start + 1] == "{"
                ):
                    next_position = self.group_end(argument_start, end) or end
                    environment = self.source[argument_start + 1 : next_position - 1]
                    if name == "begin" and environment in MATH_ENVIRONMENTS:
                        environments.append((environment, math))
                        math = True
                    elif environments and environments[-1][0] == environment:
                        _, math = environments.pop()
                elif name in {"(", "[", ")", "]"}:
                    math = name in {"(", "["}
                else:
                    parsed = self.command(command, end, math=math)
                    if parsed is not None:
                        rendered, position = parsed
                        output.append(rendered)
                        continue
                    next_position = self.opaque_arguments_end(next_position, end)
                output.append(self.source[position:next_position])
                position = next_position
            elif character == "$":
                token = "$$" if self.source.startswith("$$", position) else "$"
                output.append(token)
                position += len(token)
                math = not math
            elif self.source.startswith("^^", position):
                output.append("^^")
                position += 2
            elif math and character in "_^":
                parsed = self.argument(position + 1, end, math=True, field=True)
                if parsed is None:
                    output.append(character)
                    position += 1
                else:
                    argument, position = parsed
                    output.extend((character, argument))
            elif character == "{":
                next_position = self.group_end(position, end)
                if next_position is None:
                    output.append(self.source[position:end])
                    break
                output.extend(
                    (
                        "{",
                        self.normalize(position + 1, next_position - 1, math=math),
                        "}",
                    )
                )
                position = next_position
            else:
                output.append(character)
                position += 1
        return "".join(output)


def normalize_braces(
    source: str, commands: Mapping[str, CommandSpec] | None = None
) -> str:
    """Normalize supported arguments in ordinary LaTeX math and text contexts."""
    return BraceNormalizer(
        source, BUILTIN_COMMANDS if commands is None else commands
    ).normalize(0, len(source))
