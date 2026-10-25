"""Change-impact planning tests."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from scripts.ci import affected_books as cli
from scripts.ci import book_impact as affected
from tests.support.fixtures import git_environment

ROOT = Path(__file__).resolve().parents[2]


class AffectedBookTests(unittest.TestCase):
    manifest = {
        "schema_version": 1,
        "books": [
            {
                "slug": "alpha",
                "build": True,
            },
            {
                "slug": "beta",
                "build": True,
            },
            {
                "slug": "disabled",
                "build": False,
            },
        ],
    }
    deps = {
        "alpha": {
            "books/alpha/book.tex",
            "books/alpha/overrides/preface.tex",
            "books/alpha/references.bib",
            "books/alpha/chapters/one.tex",
            "common/styles/alpha.sty",
        },
        "beta": {
            "books/beta/book.tex",
            "common/styles/beta.sty",
        },
    }

    def plan(self, paths, old=None):
        with (
            mock.patch.object(affected, "load_manifest", return_value=self.manifest),
            mock.patch.object(
                affected, "dependencies", side_effect=lambda slug: self.deps[slug]
            ),
        ):
            return affected.plan(paths, old)

    def test_pages_workflow_advances_site_source_without_rebuilding_pdfs(self):
        result = self.plan([".github/workflows/pages.yml"])
        self.assertEqual(result["book"], [])
        self.assertTrue(result["site_changed"])

    def test_release_matrix_forces_build_after_snapshot_has_advanced(self):
        output = io.StringIO()
        with (
            mock.patch.object(affected, "load_manifest", return_value=self.manifest),
            mock.patch.object(affected, "changed_paths", return_value=[]),
            mock.patch.object(affected, "manifest_at", return_value=self.manifest),
            mock.patch.object(
                affected, "dependencies", side_effect=lambda slug: self.deps[slug]
            ),
            mock.patch.dict(os.environ, {"RELEASE_MATRIX": '{"book":["beta"]}'}),
            mock.patch.object(sys, "argv", ["ci/affected_books.py", "--base", "HEAD"]),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(cli.main(), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["book"], ["beta"])
        self.assertEqual(result["count"], 1)

    def test_book_inputs_select_one_book(self):
        for path in (
            "books/alpha/chapters/one.tex",
            "books/alpha/overrides/preface.tex",
            "books/alpha/references.bib",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.plan([path])["book"], ["alpha"])

    def test_common_style_selects_only_actual_consumer(self):
        self.assertEqual(self.plan(["common/styles/alpha.sty"])["book"], ["alpha"])

    def test_unknown_shared_assets_are_conservative_but_scaffolds_are_exempt(self):
        self.assertEqual(
            self.plan(["common/templates/diagram.png"])["book"], ["alpha", "beta"]
        )
        self.assertEqual(self.plan(["common/templates/section.tex"])["book"], [])

    def test_graphics_are_tracked_as_shared_book_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = root / "common/templates/diagram.png"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"image bytes")
            source = root / "books/alpha/book.tex"
            source.parent.mkdir(parents=True)
            source.write_text(r"\includegraphics[width=2cm]{common/templates/diagram}")
            beta = root / "books/beta/book.tex"
            beta.parent.mkdir(parents=True)
            beta.write_text("No graphic.\n")
            with (
                mock.patch.object(affected, "ROOT", root),
                mock.patch.object(
                    affected, "load_manifest", return_value=self.manifest
                ),
            ):
                self.assertEqual(
                    affected.plan(["common/templates/diagram.png"])["book"], ["alpha"]
                )
                asset.unlink()
                self.assertEqual(
                    affected.plan(["common/templates/diagram.png"])["book"],
                    ["alpha", "beta"],
                )

    def test_ci_only_helpers_select_no_books(self):
        for path in (
            "scripts/release/snapshot_base.sh",
            "scripts/release/snapshot_state.py",
            "scripts/toolchain/images/check_image_tag.sh",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.plan([path])["book"], [])

    def test_toolchain_image_inputs_select_all_books(self):
        for path in (
            ".devcontainer/Dockerfile",
            "config/toolchain.env",
            "scripts/toolchain/check_toolchain.sh",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.plan([path])["book"], ["alpha", "beta"])

    def test_shared_validation_changes_select_books_and_dependent_consumers(self):
        for path in (
            "config/validation-patterns.json",
            "scripts/repository/config/validation_patterns.py",
        ):
            with self.subTest(path=path):
                result = self.plan([path])
                self.assertEqual(result["book"], ["alpha", "beta"])
                self.assertTrue(result["site_changed"])

    def test_changed_canonical_image_reference_selects_all_books(self):
        self.assertEqual(
            self.plan(["config/container-image.txt"])["book"], ["alpha", "beta"]
        )

    def test_site_and_document_only_changes_select_no_books(self):
        paths = (
            "site/index.html",
            "scripts/site/site_pages.py",
            "scripts/lean/lean_coverage.py",
            "README.md",
            "docs/developer-workflow.md",
        )
        for path in paths:
            with self.subTest(path=path):
                result = self.plan([path])
                self.assertEqual(result["book"], [])
                self.assertEqual(result["site_changed"], not path.endswith(".md"))

    def test_snapshot_readme_change_requests_snapshot_publish_only(self):
        result = self.plan([".github/generated-pdfs-README.md"])
        self.assertEqual(result["book"], [])
        self.assertFalse(result["site_changed"])
        self.assertTrue(result["snapshot_changed"])

    def test_multiple_books(self):
        self.assertEqual(
            self.plan(["books/alpha/book.tex", "books/beta/book.tex"])["book"],
            ["alpha", "beta"],
        )

    def test_build_infrastructure_and_unknown_fall_back_to_all(self):
        for path in (
            "config/latexmkrc",
            "new-build-input.cfg",
            "common/templates/book.tex",
            "scripts/books/contents_manifest.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.plan([path])["book"], ["alpha", "beta"])

    def test_manifest_addition_selects_new_build_book(self):
        old = {
            "schema_version": 1,
            "books": [
                {
                    "slug": "beta",
                    "build": True,
                }
            ],
        }
        self.assertEqual(self.plan(["config/books.yml"], old)["book"], ["alpha"])

    def test_manifest_schema_change_falls_back_to_all(self):
        old = {
            "schema_version": 0,
            "books": [{"slug": slug, "build": True} for slug in ("alpha", "beta")],
        }
        self.assertEqual(
            self.plan(["config/books.yml"], old)["book"], ["alpha", "beta"]
        )

    def test_manifest_site_only_change_does_not_build(self):
        old = {
            "schema_version": 1,
            "books": [
                {
                    "slug": "alpha",
                    "build": True,
                },
                {
                    "slug": "beta",
                    "build": True,
                },
            ],
        }
        result = self.plan(["config/books.yml"], old)
        self.assertEqual(result["book"], [])
        self.assertTrue(result["site_changed"])

    def test_site_activation_builds_pdf_required_by_snapshot(self):
        from copy import deepcopy

        from scripts.release.snapshot_state import plan_snapshot

        previous = deepcopy(self.manifest)
        current = deepcopy(previous)
        current["books"][0]["site"] = True
        with (
            mock.patch.object(affected, "load_manifest", return_value=current),
            mock.patch.object(
                affected, "dependencies", side_effect=lambda slug: self.deps[slug]
            ),
        ):
            result = affected.plan(["config/books.yml"], previous)

        self.assertEqual(result["book"], ["alpha"])
        snapshot = plan_snapshot(
            {}, {slug: 100 for slug in result["book"]}, {"alpha", "beta"}, {"alpha"}
        )
        self.assertEqual(snapshot.replace, ("alpha",))
        with (
            mock.patch.object(affected, "load_manifest", return_value=previous),
            mock.patch.object(
                affected, "dependencies", side_effect=lambda slug: self.deps[slug]
            ),
        ):
            self.assertEqual(affected.plan(["config/books.yml"], current)["book"], [])

    def test_deleted_or_renamed_book_uses_safe_fallback(self):
        old = {
            "schema_version": 1,
            "books": [{"slug": slug, "build": True} for slug in ("old-alpha", "beta")],
        }
        self.assertEqual(
            self.plan(["config/books.yml", "books/old-alpha/book.tex"], old)["book"],
            ["alpha", "beta"],
        )

    def test_consecutive_push_planner_uses_cumulative_snapshot_diff(self):
        with mock.patch.object(
            affected, "shared_changed_paths", return_value=["books/alpha/book.tex"]
        ) as output:
            self.assertEqual(
                affected.changed_paths("snapshot-sha", "latest-sha"),
                ["books/alpha/book.tex"],
            )
        output.assert_called_once_with("snapshot-sha", "latest-sha", root=affected.ROOT)

    def test_resolver_tracks_common_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "books" / "alpha" / "book.tex"
            source.parent.mkdir(parents=True)
            references = source.parent / "references.bib"
            references.write_text("", encoding="utf-8")
            (root / "common" / "styles").mkdir(parents=True)
            (root / "common" / "styles" / "shared.sty").write_text("", encoding="utf-8")
            with mock.patch.object(affected, "ROOT", root):
                self.assertEqual(
                    affected._resolve_tex("references", source, "addbibresource"),
                    [references.resolve()],
                )
                self.assertEqual(
                    affected._resolve_tex(
                        "shared",
                        source,
                        "RequirePackage",
                    ),
                    [(root / "common" / "styles" / "shared.sty").resolve()],
                )

    def test_resolver_tracks_book_local_style(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "books" / "alpha" / "book.tex"
            local_style = root / "books" / "alpha" / "overrides" / "style.sty"
            local_style.parent.mkdir(parents=True)
            local_style.write_text("", encoding="utf-8")
            with mock.patch.object(affected, "ROOT", root):
                self.assertEqual(
                    affected._resolve_tex("overrides/style", source, "usepackage"),
                    [local_style.resolve()],
                )

    def test_changed_paths_preserves_both_rename_paths_and_unicode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*arguments):
                return subprocess.run(
                    ["git", *arguments],
                    cwd=root,
                    env=git_environment(),
                    timeout=10,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            git("init", "-q")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            old = "books/alpha/한글 section.tex"
            new = "docs/moved\nsection.tex"
            (root / old).parent.mkdir(parents=True)
            (root / old).write_text("unchanged content\n")
            git("add", ".")
            git("commit", "-qm", "before")
            base = git("rev-parse", "HEAD")
            (root / new).parent.mkdir(parents=True)
            (root / old).rename(root / new)
            git("add", "-A")
            git("commit", "-qm", "after")
            with mock.patch.object(affected, "ROOT", root):
                paths = affected.changed_paths(base, "HEAD")
                assert paths is not None
                self.assertEqual(set(paths), {old, new})

    def test_invalid_historical_manifests_fall_back_without_creating_paths(self):
        for text in (
            "",
            "[]",
            "books: null",
            "books: [null]",
            "books: [",
            "books: [{slug: ../outside}]",
            "books: [{slug: /tmp/outside}]",
            "books: [{slug: alpha}, {slug: alpha}]",
        ):
            with (
                self.subTest(text=text),
                mock.patch.object(affected, "git_output", return_value=text),
                mock.patch.object(Path, "mkdir") as mkdir,
            ):
                self.assertIsNone(affected.manifest_at("base"))
            mkdir.assert_not_called()

    def test_historical_manifest_validates_deleted_book_metadata(self):
        manifest = {
            "schema_version": 1,
            "defaults": {
                "author": "Author",
                "build": True,
                "check": True,
                "release": False,
                "site": False,
            },
            "books": [
                {
                    "slug": "deleted",
                    "title": "Deleted",
                    "version": "1.0.0",
                    "status": "draft",
                    "order": 10,
                }
            ],
        }
        with mock.patch.object(
            affected, "git_output", return_value=yaml.safe_dump(manifest)
        ):
            result = affected.manifest_at("base")
        assert result is not None
        self.assertEqual(result["books"][0]["slug"], "deleted")
        self.assertTrue(result["books"][0]["build"])

    def test_empty_change_has_empty_matrix(self):
        self.assertEqual(self.plan([])["count"], 0)

    def test_manual_or_missing_comparison_builds_all(self):
        self.assertEqual(self.plan(None)["book"], ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
