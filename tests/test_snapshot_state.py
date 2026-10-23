"""Validate and stage snapshots without changing the previous set on failure."""

from __future__ import annotations

import importlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
state = importlib.import_module("snapshot_state")


class SnapshotStateTests(unittest.TestCase):
    def test_plan_keeps_unchanged_books_and_prunes_retired_books(self) -> None:
        plan = state.plan_snapshot(
            {"alpha": 10, "beta": 20, "retired": 30},
            {"alpha": 40, "hidden": 50},
            {"alpha", "beta", "retired", "hidden"},
            {"alpha", "beta"},
        )
        self.assertEqual(plan.replace, ("alpha",))
        self.assertEqual(plan.remove, ("hidden", "retired"))

    def test_build_plan_requires_exact_updates_even_when_previous_pdf_exists(self):
        for updated in ({}, {"beta": 10}, {"alpha": 10, "beta": 10}):
            with (
                self.subTest(updated=updated),
                self.assertRaisesRegex(
                    ValueError, "artifacts differ from the build plan"
                ),
            ):
                state.plan_snapshot(
                    {"alpha": 20, "beta": 20},
                    updated,
                    {"alpha", "beta"},
                    {"alpha", "beta"},
                    {"alpha"},
                )
        self.assertEqual(
            state.plan_snapshot(
                {"alpha": 20, "beta": 20},
                {"alpha": 10},
                {"alpha", "beta"},
                {"alpha", "beta"},
                {"alpha"},
            ).replace,
            ("alpha",),
        )

    def test_failed_copy_or_install_preserves_previous_set_and_allows_retry(
        self,
    ) -> None:
        for failure in ("copy", "install", "interrupt", "restore"):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                snapshot = root / "snapshot"
                (snapshot / "pdf").mkdir(parents=True)
                updates = root / "updated-pdfs"
                updates.mkdir()
                for slug in ("alpha", "beta"):
                    (snapshot / "pdf" / f"{slug}.pdf").write_bytes(b"old")
                    (updates / f"{slug}.pdf").write_bytes(b"new")
                manifest = {
                    "books": [
                        {"slug": slug, "site": True} for slug in ("alpha", "beta")
                    ]
                }
                copyfile = shutil.copyfile
                replace = state.os.replace

                def copy(source, target, **options):
                    if failure == "copy" and Path(source) == updates / "beta.pdf":
                        raise OSError("copy failed")
                    return copyfile(source, target, **options)

                def install(source, target):
                    if failure == "restore" and Path(source).name in {
                        "next",
                        "previous",
                    }:
                        raise OSError("replace failed")
                    if Path(source).name == "next":
                        if failure == "install":
                            raise OSError("install failed")
                        if failure == "interrupt":
                            raise KeyboardInterrupt()
                    return replace(source, target)

                with patch.object(state, "load_manifest", return_value=manifest):
                    with (
                        patch.object(state.shutil, "copyfile", side_effect=copy),
                        patch.object(state.os, "replace", side_effect=install),
                        self.assertRaises(
                            KeyboardInterrupt if failure == "interrupt" else OSError
                        ),
                    ):
                        state.prepare(snapshot, updates)
                    if failure == "restore":
                        backup = next(snapshot.glob(".pdf-staging-*/previous"))
                        for slug in ("alpha", "beta"):
                            self.assertEqual(
                                (backup / f"{slug}.pdf").read_bytes(), b"old"
                            )
                        replace(backup, snapshot / "pdf")
                        shutil.rmtree(backup.parent)
                    for slug in ("alpha", "beta"):
                        self.assertEqual(
                            (snapshot / "pdf" / f"{slug}.pdf").read_bytes(), b"old"
                        )
                    self.assertEqual(list(snapshot.glob(".pdf-staging-*")), [])
                    state.prepare(snapshot, updates)
                    for slug in ("alpha", "beta"):
                        self.assertEqual(
                            (snapshot / "pdf" / f"{slug}.pdf").read_bytes(), b"new"
                        )

    def test_non_file_artifact_is_rejected_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot"
            (snapshot / "pdf").mkdir(parents=True)
            (snapshot / "pdf/alpha.pdf").write_bytes(b"old")
            updates = root / "updated-pdfs"
            (updates / "alpha.pdf").mkdir(parents=True)
            with (
                patch.object(
                    state,
                    "load_manifest",
                    return_value={"books": [{"slug": "alpha", "site": True}]},
                ),
                self.assertRaisesRegex(ValueError, "PDF artifact is missing or empty"),
            ):
                state.prepare(snapshot, updates)
            self.assertEqual((snapshot / "pdf/alpha.pdf").read_bytes(), b"old")
