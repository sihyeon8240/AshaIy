"""Validate macro manifests and render their declarations deterministically."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from scripts.latex.command_specs import RESERVED_COMMANDS, ArgumentSpec, CommandSpec
from scripts.latex.latex_scan import (
    has_balanced_braces,
    is_escaped,
    source_spans,
    without_comments,
)
from scripts.repository.source_reads import field_mapping, parse_yaml, read_text

NAME = re.compile(r"[A-Z][A-Za-z]*")
MODES = {"math", "text", "opaque"}


@dataclass(frozen=True)
class MacroDeclaration:
    name: str
    kind: str
    spec: CommandSpec
    body: str = ""
    left: str = ""
    right: str = ""
    text: str = ""
    limits: bool = False
    after: str = ""


def tex_value(value: object, context: str, *, parameters: int = 0) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a TeX string")
    clean = without_comments(value)
    if not has_balanced_braces(clean):
        raise ValueError(f"{context} must have balanced braces")
    position = 0
    while position < len(clean):
        if clean[position] != "#" or is_escaped(clean, position):
            position += 1
            continue
        following = clean[position + 1 : position + 2]
        if following == "#":
            position += 2
            continue
        if following not in tuple(str(index) for index in range(1, parameters + 1)):
            raise ValueError(
                f"{context} has an invalid parameter reference at #{following}"
            )
        position += 2
    return value


def arguments(value: object, context: str, *, paired: bool) -> tuple[ArgumentSpec, ...]:
    if not isinstance(value, list) or len(value) > 9 or (paired and not value):
        raise ValueError(f"{context} must list {'1–9' if paired else '0–9'} arguments")
    result = []
    for index, raw in enumerate(value):
        label = f"{context}[{index}]"
        item = field_mapping(raw, label)
        kind = item.get("kind")
        allowed = (
            {"kind", "mode", "default"} if kind == "optional" else {"kind", "mode"}
        )
        if (
            set(item) != allowed
            or not isinstance(item.get("mode"), str)
            or item["mode"] not in MODES
        ):
            raise ValueError(
                f"{label} requires kind and mode, plus default for optional arguments"
            )
        default = None
        if kind == "optional" and index == 0 and not paired:
            default = tex_value(item["default"], f"{label}.default")
            depth = 0
            for position, character in enumerate(without_comments(default)):
                if is_escaped(default, position):
                    continue
                if character == "{":
                    depth += 1
                elif character == "}":
                    depth -= 1
                elif character == "]" and depth == 0:
                    raise ValueError(f"{label}.default: brace literal ] tokens")
        elif kind != "mandatory":
            raise ValueError(
                f"{label}: only one leading optional argument is supported"
            )
        result.append(ArgumentSpec(kind, item["mode"], default))
    return tuple(result)


def declaration(name: str, value: object, context: str) -> MacroDeclaration:
    if (
        not isinstance(name, str)
        or not NAME.fullmatch(name)
        or name in RESERVED_COMMANDS
    ):
        raise ValueError(
            f"{context}: expected a non-reserved alphabetic command name "
            "starting with an uppercase letter"
        )
    item = field_mapping(value, context)
    kind = item.get("kind")
    required = {
        "command": {"kind", "arguments", "body"},
        "operator": {"kind", "text"},
        "paired_delimiter": {"kind", "left", "right"},
        "paired_delimiter_x": {"kind", "left", "right", "arguments", "body"},
    }
    if not isinstance(kind, str) or kind not in required:
        raise ValueError(f"{context}.kind is unsupported")
    extra = {"script_atom"}
    if kind == "command":
        extra.add("context")
    if kind == "operator":
        extra.add("limits")
    if kind == "paired_delimiter_x":
        extra.add("after")
    if not required[kind] <= item.keys() or item.keys() - required[kind] - extra:
        raise ValueError(f"{context}: missing or unsupported fields for {kind}")
    script_atom = item.get("script_atom", False)
    if type(script_atom) is not bool:
        raise ValueError(f"{context}.script_atom must be a boolean")
    mode = item.get("context", "math")
    if not isinstance(mode, str) or mode not in {"math", "text", "any"}:
        raise ValueError(f"{context}.context must be math, text, or any")
    paired = kind.startswith("paired_delimiter")
    if kind == "paired_delimiter":
        params = (ArgumentSpec(),)
    elif kind in {"command", "paired_delimiter_x"}:
        params = arguments(item["arguments"], f"{context}.arguments", paired=paired)
    else:
        params = ()
    body = tex_value(item.get("body", ""), f"{context}.body", parameters=len(params))
    after = tex_value(item.get("after", ""), f"{context}.after", parameters=len(params))
    left = tex_value(item.get("left", ""), f"{context}.left")
    right = tex_value(item.get("right", ""), f"{context}.right")
    text = tex_value(item.get("text", ""), f"{context}.text")
    if kind == "operator" and not text.strip():
        raise ValueError(f"{context}.text must not be empty")
    if paired and (not left.strip() or not right.strip()):
        raise ValueError(
            f"{context}: delimiters must not be empty (use . for an empty fence)"
        )
    limits = item.get("limits", False)
    if type(limits) is not bool:
        raise ValueError(f"{context}.limits must be a boolean")
    if paired:
        params = (
            ArgumentSpec("star", "opaque"),
            ArgumentSpec("optional", "opaque"),
            *params,
        )
    spec = CommandSpec(params, mode, script_atom, paired)
    return MacroDeclaration(name, kind, spec, body, left, right, text, limits, after)


def load_macros(path: Path) -> dict[str, MacroDeclaration]:
    text = read_text(path)
    try:
        data = field_mapping(parse_yaml(text), str(path))
        tree = yaml.compose(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        location = f":{mark.line + 1}:{mark.column + 1}" if mark is not None else ""
        raise ValueError(f"{path}{location}: {error}") from error
    if (
        set(data) != {"schema_version", "macros"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise ValueError(f"{path}:1: expected schema_version: 1 and macros")
    entries = field_mapping(data["macros"], f"{path}: macros")
    if not entries:
        raise ValueError(
            f"{path}: macros must not be empty; omit unused book manifests"
        )
    lines = {}
    if isinstance(tree, yaml.MappingNode):
        for key, node in tree.value:
            if key.value == "macros" and isinstance(node, yaml.MappingNode):
                lines = {key.value: key.start_mark.line + 1 for key, _ in node.value}
    return {
        name: declaration(name, value, f"{path}:{lines.get(name, 1)}: macros.{name}")
        for name, value in entries.items()
    }


def render_macros(
    declarations: dict[str, MacroDeclaration], source: str, package: str
) -> str:
    lines = [
        f"% Generated from {source}; do not edit.",
        r"\NeedsTeXFormat{LaTeX2e}",
        rf"\ProvidesPackage{{{package}}}",
        "",
    ]
    for macro in declarations.values():
        name = "{" + "\\" + macro.name + "}"
        if macro.kind == "operator":
            star = "*" if macro.limits else ""
            line = rf"\DeclareMathOperator{star}{name}" + tex_group(macro.text)
        elif macro.kind == "paired_delimiter":
            line = (
                rf"\DeclarePairedDelimiter{name}"
                + tex_group(macro.left)
                + tex_group(macro.right)
            )
        elif macro.kind == "paired_delimiter_x":
            count = sum(
                argument.kind == "mandatory" for argument in macro.spec.arguments
            )
            command = "DeclarePairedDelimiterX"
            before = ""
            after = ""
            if macro.after:
                command += "PP"
                before = "{}"
                after = tex_group(macro.after)
            line = (
                rf"\{command}{name}[{count}]"
                + before
                + tex_group(macro.left)
                + tex_group(macro.right)
                + after
                + tex_group(macro.body)
            )
        else:
            count = len(macro.spec.arguments)
            signature = f"[{count}]" if count else ""
            if count and macro.spec.arguments[0].kind == "optional":
                signature += tex_group(str(macro.spec.arguments[0].default), "[", "]")
            line = rf"\newcommand{name}{signature}" + tex_group(macro.body)
        lines.append(line)
    return "\n".join(lines) + "\n"


def tex_group(value: str, opening: str = "{", closing: str = "}") -> str:
    if any(
        span.kind == "comment" and span.end == len(value)
        for span in source_spans(value)
    ):
        value += "\n"
    return opening + value + closing
