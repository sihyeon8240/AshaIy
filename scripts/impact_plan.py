"""Explain source and cumulative PDF selections with independent Git baselines."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.ci_changes import ROOT, changed_paths, consumer_selections
from scripts.source_impact import lean_reasons


def revision(reference: str) -> str | None:
    if not reference:
        return None
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def comparison(base: str, head: str) -> tuple[dict, list[str] | None]:
    resolved = revision(base)
    paths = changed_paths(resolved, head, root=ROOT)
    return {
        "requested_base": base or None,
        "base": resolved,
        "head": head,
        "available": paths is not None,
        "paths": sorted(paths) if paths is not None else None,
    }, paths


def source_selection(
    paths: list[str] | None,
    base: str,
    head: str = "HEAD",
    *,
    root: Path | None = None,
) -> dict:
    consumers = consumer_selections(paths, root=root or ROOT)
    reasons = lean_reasons(paths, base, head, root=root)
    consumers["lean"] = {"selected": bool(reasons), "reasons": reasons}
    return consumers


def pdf_selection(
    paths: list[str] | None,
    base: str | None,
    *,
    release_books: tuple[str, ...] = (),
    explain: bool = False,
) -> dict:
    from scripts import book_impact

    result = book_impact.plan(
        paths,
        book_impact.manifest_at(base),
        release_books=release_books,
        explain=explain,
    )
    result["book"] = sorted(result["book"])
    return result


def create_plan(
    source_base: str,
    pdf_base: str,
    *,
    release_books: tuple[str, ...] = (),
) -> dict:
    head = revision("HEAD")
    if head is None:
        raise ValueError("impact planning requires a committed Git checkout")
    source_comparison, source_paths = comparison(source_base, head)
    pdf_comparison, pdf_paths = comparison(pdf_base, head)
    source = source_selection(
        source_paths, source_comparison["base"] or "", head, root=ROOT
    )
    pdf = pdf_selection(
        pdf_paths,
        pdf_comparison["base"],
        release_books=release_books,
        explain=True,
    )
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return {
        "schema_version": 1,
        "head": head,
        "working_tree_dirty": bool(dirty.stdout),
        "source": {"comparison": source_comparison, "consumers": source},
        "pdf": {"comparison": pdf_comparison, **pdf},
        "release": {"requested_books": sorted(set(release_books))},
    }
