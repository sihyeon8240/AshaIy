"""Describe workspace cache volumes shared by both Dev Container entry points."""

from __future__ import annotations

import csv

CACHE_DIRECTORIES = ("lean/.lake", ".cache", ".hypothesis")


def mount_options(mount: str | dict) -> dict[str, str]:
    if isinstance(mount, dict):
        options = dict(mount)
    else:
        options = {}
        for field in next(csv.reader([mount])):
            key, _, value = field.partition("=")
            options[key] = value

    for alias, name in (("src", "source"), ("dst", "target"), ("destination", "target")):
        if alias in options:
            options[name] = options.pop(alias)
    return options


def cache_mounts(lean_version: str) -> list[str]:
    names = (f"lake-v{lean_version}", "cache-v1", "hypothesis-v1")
    return [
        f"source=ashaiy-${{devcontainerId}}-{name},"
        f"target=${{containerWorkspaceFolder}}/{directory},type=volume,volume-nocopy"
        for directory, name in zip(CACHE_DIRECTORIES, names, strict=True)
    ]


def synchronize_cache_mounts(configuration: dict, lean_version: str) -> None:
    targets = {f"${{containerWorkspaceFolder}}/{directory}" for directory in CACHE_DIRECTORIES}
    preserved = [
        mount for mount in configuration.get("mounts", []) if mount_options(mount).get("target") not in targets
    ]
    configuration["mounts"] = [*preserved, *cache_mounts(lean_version)]
