"""Conservative source-check selection, independent of output formatting."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from scripts.ci.ci_changes import is_documentation
from scripts.repository.config.validation_patterns import validation_pattern
from scripts.repository.path_policy import SAFE_PATHS, SITE_FILES

ARTIFACT_ACTION = re.compile(
    r"(?m)^([ \t]*(?:-[ \t]+)?uses:[ \t]+actions/(?:upload|download)-artifact)"
    rf"@{validation_pattern('git_commit')}[ \t]*(?:#[^\n]*)?$"
)


def git_text(*arguments: str, root: Path | None = None) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, text=True, capture_output=True
    ).stdout


def lean_reasons(
    paths: list[str] | None,
    base: str,
    head: str = "HEAD",
    *,
    root: Path | None = None,
) -> list[dict]:
    if paths is None:
        return [{"reason": "comparison unavailable; safe full check", "paths": []}]

    reasons = []
    for path in paths:
        if (
            path in SAFE_PATHS
            or path in SITE_FILES
            or path.startswith("site/")
            or (path.startswith("tests/") and path.endswith(".py"))
            or is_documentation(path)
        ):
            continue
        if path.startswith(".github/workflows/") and path.endswith(".yml"):
            try:
                before = git_text("show", f"{base}:{path}", root=root)
                after = git_text("show", f"{head}:{path}", root=root)
            except subprocess.CalledProcessError:
                reasons.append(
                    {"reason": "workflow comparison unavailable", "paths": [path]}
                )
                continue
            if ARTIFACT_ACTION.sub(r"\1@PIN", before) == ARTIFACT_ACTION.sub(
                r"\1@PIN", after
            ):
                continue
        reasons.append(
            {"reason": "change not exempt from Lean checks", "paths": [path]}
        )
    return reasons


def needs_lean(paths: list[str], base: str, head: str = "HEAD") -> bool:
    return bool(lean_reasons(paths, base, head))
