"""Validate shared theorem declarations and render their LaTeX package."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from scripts.latex.latex_scan import without_comments
from scripts.latex.macro_manifest import tex_group, tex_value
from scripts.repository.source_reads import field_mapping, read_yaml

NAME = re.compile(r"[a-z][a-z0-9]*\*?")
LIST_ENVIRONMENTS = {"enumerate", "itemize", "description"}
RESERVED = LIST_ENVIRONMENTS | {
    "document",
    "abstract",
    "figure",
    "table",
    "tabular",
    "list",
    "trivlist",
    "minipage",
    "equation",
    "align",
    "gather",
    "displaymath",
    "math",
    "verbatim",
    "center",
    "flushleft",
    "flushright",
    "quote",
    "quotation",
    "verse",
}


@dataclass(frozen=True)
class TheoremEnvironment:
    name: str
    kind: str
    space_after: str
    break_before_initial_list: bool
    title: str = ""
    style: str = ""
    within: str | None = None
    shared: str | None = None
    cref: tuple[str, str] | None = None

    @property
    def numbered(self) -> bool:
        return self.within is not None or self.shared is not None


@dataclass(frozen=True)
class TheoremManifest:
    environments: dict[str, TheoremEnvironment]
    list_environments: tuple[str, ...]

    @property
    def numbered_environments(self) -> tuple[str, ...]:
        return tuple(env.name for env in self.environments.values() if env.numbered)


def fields(value: object, context: str, required: set[str], optional: set[str] | frozenset[str] = frozenset()) -> dict:
    item = field_mapping(value, context)
    if not required <= item.keys() or item.keys() - required - optional:
        raise ValueError(f"{context}: missing or unsupported fields")
    return item


def inline_tex(value: object, context: str) -> str:
    text = tex_value(value, context)
    if not text.strip() or "\n" in text or "\r" in text or without_comments(text) != text:
        raise ValueError(f"{context} must be nonempty single-line TeX without comments")
    return text


def spacing(item: dict, context: str) -> tuple[str, bool]:
    space = item["space_after"]
    if not isinstance(space, str) or space not in {"none", "bigskip"}:
        raise ValueError(f"{context}.space_after must be none or bigskip")
    initial_list = item["break_before_initial_list"]
    if type(initial_list) is not bool:
        raise ValueError(f"{context}.break_before_initial_list must be a boolean")
    return space, initial_list


def load_theorems(path: Path) -> TheoremManifest:
    try:
        data = fields(read_yaml(path), str(path), {"schema_version", "defaults", "list_environments", "environments"})
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        location = f":{mark.line + 1}:{mark.column + 1}" if mark is not None else ""
        raise ValueError(f"{path}{location}: {error}") from error
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError(f"{path}: expected schema_version: 1")
    policy_fields = {"space_after", "break_before_initial_list"}
    defaults = fields(data["defaults"], f"{path}: defaults", policy_fields)
    spacing(defaults, f"{path}: defaults")
    lists = data["list_environments"]
    if (
        not isinstance(lists, list)
        or any(not isinstance(name, str) or name not in LIST_ENVIRONMENTS for name in lists)
        or len(lists) != len(set(lists))
    ):
        raise ValueError(f"{path}: list_environments must uniquely list enumerate, itemize, or description")
    entries = field_mapping(data["environments"], f"{path}: environments")
    if not entries:
        raise ValueError(f"{path}: environments must not be empty")
    environments: dict[str, TheoremEnvironment] = {}
    for name, raw in entries.items():
        context = f"{path}: environments.{name}"
        if not NAME.fullmatch(name) or name in RESERVED:
            raise ValueError(f"{context}: invalid or reserved environment name")
        item = field_mapping(raw, context)
        if item.get("kind") == "provided":
            fields(item, context, {"kind", "provider"}, policy_fields)
            if name != "proof" or item["provider"] != "amsthm":
                raise ValueError(f"{context}: only proof provided by amsthm is supported")
        elif item.get("kind") == "theorem":
            fields(item, context, {"kind", "title", "style", "counter"}, policy_fields | {"cref"})
            if name == "proof":
                raise ValueError(f"{context}: proof is provided by amsthm")
        else:
            raise ValueError(f"{context}.kind must be theorem or provided")
        space, initial_list = spacing(defaults | item, context)
        if item["kind"] == "provided":
            environments[name] = TheoremEnvironment(name, "provided", space, initial_list)
            continue
        title = inline_tex(item["title"], f"{context}.title")
        style = item["style"]
        if not isinstance(style, str) or style not in {"plain", "definition", "remark"}:
            raise ValueError(f"{context}.style must be plain, definition, or remark")
        within = shared = None
        if item["counter"] is not None:
            counter = field_mapping(item["counter"], f"{context}.counter")
            if set(counter) == {"within"}:
                within = counter["within"]
                if not isinstance(within, str) or within not in {"chapter", "section"}:
                    raise ValueError(f"{context}.counter.within must be chapter or section")
            elif set(counter) == {"shared"}:
                shared = counter["shared"]
                if not isinstance(shared, str) or shared not in environments or not environments[shared].numbered:
                    raise ValueError(f"{context}.counter.shared must name an earlier numbered theorem")
            else:
                raise ValueError(f"{context}.counter must be null or contain exactly one of within and shared")
        cref = None
        if "cref" in item:
            names = fields(item["cref"], f"{context}.cref", {"singular", "plural"})
            cref = (
                inline_tex(names["singular"], f"{context}.cref.singular"),
                inline_tex(names["plural"], f"{context}.cref.plural"),
            )
        environments[name] = TheoremEnvironment(
            name, "theorem", space, initial_list, title, style, within, shared, cref
        )
    return TheoremManifest(environments, tuple(lists))


def render_theorems(manifest: TheoremManifest) -> str:
    lines = [
        "% Generated from common/styles/theorems.yml; do not edit.",
        r"\NeedsTeXFormat{LaTeX2e}",
        r"\ProvidesPackage{generated-theorems}",
        "",
    ]
    style = None
    for env in manifest.environments.values():
        if env.kind != "theorem":
            continue
        if style != env.style:
            lines.extend([rf"\theoremstyle{{{env.style}}}", ""])
            style = env.style
        if env.shared:
            declaration = rf"\newtheorem{{{env.name}}}[{env.shared}]" + tex_group(env.title)
        elif env.within:
            declaration = rf"\newtheorem{{{env.name}}}" + tex_group(env.title) + f"[{env.within}]"
        else:
            declaration = rf"\newtheorem*{{{env.name}}}" + tex_group(env.title)
        lines.extend([declaration, ""])
    for env in manifest.environments.values():
        if env.space_after == "bigskip":
            lines.append(rf"\AddToHook{{env/{env.name}/after}}{{\par\bigskip}}")
        if env.break_before_initial_list:
            lines.append(rf"\expandafter\let\csname textbook@listhead@{env.name}\endcsname\@empty")
    lines.append("")
    for name in manifest.list_environments:
        lines.append(rf"\AddToHook{{env/{name}/before}}{{\textbook@breakbeforelist{{{name}}}}}")
    lines.append("")
    for env in manifest.environments.values():
        if env.cref:
            singular, plural = env.cref
            lines.append(rf"\crefname{{{env.name}}}" + tex_group(singular) + tex_group(plural))
            lines.append(
                rf"\Crefname{{{env.name}}}"
                + tex_group(singular[0].upper() + singular[1:])
                + tex_group(plural[0].upper() + plural[1:])
            )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
