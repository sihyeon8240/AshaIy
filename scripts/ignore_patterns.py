"""Render consumer-specific exclusions from shared pattern groups."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from scripts.source_reads import read_yaml
from scripts.validation_patterns import validation_pattern

PATTERN = re.compile(r"[A-Za-z0-9_.*?/~+-]+")
HEADER = "# Generated from config/ignore-patterns.yml; do not edit.\n"
EDITOR_PROFILES = {
    "vscode-search": "search.exclude",
    "vscode-watcher": "files.watcherExclude",
}


def load_patterns(path: Path) -> dict[str, list[str]]:
    try:
        config = read_yaml(path)
    except yaml.YAMLError as error:
        raise ValueError(f"{path}: invalid YAML: {error}") from error
    if (
        not isinstance(config, dict)
        or set(config) != {"schema_version", "groups", "profiles"}
        or type(config["schema_version"]) is not int
        or config["schema_version"] != 1
    ):
        raise ValueError(f"{path}: expected ignore-pattern schema version 1")

    groups, profiles = config["groups"], config["profiles"]
    if not isinstance(groups, dict) or not isinstance(profiles, dict):
        raise ValueError(f"{path}: groups and profiles must be mappings")
    if set(profiles) != {
        "git",
        "docker",
        "tree",
        "cleanup-files",
        "cleanup-prune",
        *EDITOR_PROFILES,
    }:
        raise ValueError(f"{path}: unexpected consumer profiles")
    for name, patterns in groups.items():
        if not isinstance(name, str) or not isinstance(patterns, list) or not patterns:
            raise ValueError(f"{path}: expected named, nonempty pattern groups")
        for pattern in patterns:
            if not isinstance(pattern, str) or not PATTERN.fullmatch(pattern):
                raise ValueError(f"{path}: invalid pattern in group {name}")

    result = {}
    for consumer, names in profiles.items():
        if not isinstance(names, list) or not names:
            raise ValueError(f"{path}: {consumer} must select pattern groups")
        patterns = []
        for name in names:
            if not isinstance(name, str) or name not in groups:
                raise ValueError(f"{path}: unknown group in {consumer} profile")
            patterns.extend(groups[name])
        if len(patterns) != len(set(patterns)):
            raise ValueError(f"{path}: duplicate patterns in {consumer} profile")
        result[consumer] = patterns
    if any("/" in pattern for pattern in result["cleanup-files"]):
        raise ValueError(f"{path}: cleanup-files must contain filename patterns")
    for pattern in result["cleanup-prune"]:
        if not re.fullmatch(validation_pattern("relative_path"), pattern) or any(
            part in {".", ".."} for part in pattern.split("/")
        ):
            raise ValueError(f"{path}: cleanup-prune must contain relative directories")
    return result


def rendered_ignore_consumers(root: Path) -> dict[Path, str]:
    patterns = load_patterns(root / "config/ignore-patterns.yml")
    settings_path = root / ".vscode/settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    for profile, key in EDITOR_PROFILES.items():
        settings[key] = dict.fromkeys(patterns[profile], True)

    return {
        root / "config/generated/cleanup-files.txt": "\n".join(
            patterns["cleanup-files"]
        )
        + "\n",
        root / "config/generated/cleanup-prune.txt": "\n".join(
            patterns["cleanup-prune"]
        )
        + "\n",
        root / ".gitignore": HEADER + "\n".join(patterns["git"]) + "\n",
        root / ".devcontainer/Dockerfile.dockerignore": HEADER
        + "\n".join(patterns["docker"])
        + "\n",
        settings_path: json.dumps(settings, indent=2) + "\n",
    }
