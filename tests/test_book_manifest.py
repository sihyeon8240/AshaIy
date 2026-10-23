"""Manifest normalization, validation, export, and diagnostic tests."""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from test_support import write_yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import book_manifest as books_module  # noqa: E402
from book_manifest import load_manifest, manifest_warnings  # noqa: E402

books_cli = importlib.import_module("books")


class ManifestWarningTests(unittest.TestCase):
    def test_suspicious_combinations_are_warnings(self) -> None:
        manifest = {
            "books": [
                {
                    "slug": "archived-a",
                    "status": "archived",
                    "order": 10,
                    "release": True,
                    "site": True,
                },
                {
                    "slug": "draft-b",
                    "status": "draft",
                    "order": 10,
                    "release": True,
                    "site": False,
                },
            ]
        }

        warnings = manifest_warnings(manifest)

        self.assertEqual(len(warnings), 4)
        self.assertTrue(any("duplicate order 10" in warning for warning in warnings))
        self.assertTrue(
            any("archived but release=true" in warning for warning in warnings)
        )
        self.assertTrue(
            any("archived but site=true" in warning for warning in warnings)
        )
        self.assertTrue(
            any("draft but release=true" in warning for warning in warnings)
        )


class ManifestModuleTests(unittest.TestCase):
    def fixture(
        self, book: dict[str, object], defaults: dict[str, object] | None = None
    ):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        book = {"version": "1.0.0", **book}
        slug = str(book.get("slug", "sample"))
        book_dir = root / "books" / slug
        book_dir.mkdir(parents=True)
        (book_dir / "book.tex").write_text("", encoding="utf-8")
        manifest_path = root / "config/books.yml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        write_yaml(
            manifest_path,
            {
                "schema_version": 1,
                "defaults": defaults
                if defaults is not None
                else {
                    "author": "Sample Author",
                    "build": True,
                    "check": False,
                    "release": False,
                    "site": True,
                },
                "books": [book],
            },
        )
        return root, manifest_path, book_dir

    def test_load_manifest_merges_defaults_and_sorts(self) -> None:
        root, path, _ = self.fixture(
            {
                "slug": "sample",
                "title": "Sample",
                "status": "draft",
                "order": 10,
                "check": True,
            }
        )
        book = load_manifest(path, root)["books"][0]
        self.assertTrue(book["build"])
        self.assertTrue(book["check"])
        self.assertFalse(book["release"])
        self.assertTrue(book["site"])
        self.assertEqual(book["label_prefix"], "s")

    def test_version_and_status_defaults_allow_book_overrides(self) -> None:
        root, path, _ = self.fixture({"slug": "sample", "title": "Sample", "order": 10})
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        manifest["defaults"].update(version="0.1.0", status="draft")
        del manifest["books"][0]["version"]
        write_yaml(path, manifest)

        book = load_manifest(path, root)["books"][0]
        self.assertEqual((book["version"], book["status"]), ("0.1.0", "draft"))

        manifest["books"][0].update(version="0.2.0", status="review")
        write_yaml(path, manifest)
        book = load_manifest(path, root)["books"][0]
        self.assertEqual((book["version"], book["status"]), ("0.2.0", "review"))

    def test_manifest_accepts_semver_hyphenated_prereleases(self) -> None:
        for version in ("1.2.3--alpha", "1.2.3-alpha--beta", "1.2.3-rc.1"):
            with self.subTest(version=version):
                root, path, _ = self.fixture(
                    {
                        "slug": "sample",
                        "title": "Sample",
                        "status": "draft",
                        "order": 10,
                        "version": version,
                    }
                )
                self.assertEqual(
                    load_manifest(path, root)["books"][0]["version"], version
                )

    def test_load_manifest_rejects_invalid_fields(self) -> None:
        for override, diagnostic in (
            ({"unknown": 1}, "unknown field"),
            ({"build": "yes"}, "must be boolean"),
            ({"version": "1.0"}, "invalid version"),
            ({"version": "01.2.3"}, "invalid version"),
            ({"version": "1.2.3-01"}, "invalid version"),
            ({"author": ""}, "author"),
        ):
            with self.subTest(override=override):
                book = {
                    "slug": "sample",
                    "title": "Sample",
                    "status": "draft",
                    "order": 10,
                    **override,
                }
                root, path, _ = self.fixture(book)
                with self.assertRaisesRegex(ValueError, diagnostic):
                    load_manifest(path, root)


class ManifestFixture(unittest.TestCase):
    def make_repository(
        self,
        records: list[dict],
    ) -> tuple[Path, Path]:
        root = Path(self.directory.name)
        for record in records:
            slug = record["slug"]
            book_dir = root / "books" / slug
            book_dir.mkdir(parents=True, exist_ok=True)
            (book_dir / "book.tex").write_text("", encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "defaults": {
                "author": "Sample Author",
                "build": True,
                "check": True,
                "release": False,
                "site": False,
            },
            "books": records,
        }
        path = root / "config/books.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        return root, path

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.directory.cleanup()


class ManifestRecordTests(ManifestFixture):
    def test_list_warnings_preserve_json_targets_and_diagnostics(self):
        root, path = self.make_repository(
            [
                self.base("alpha", release=True),
                self.base("beta", order=20, build=False, check=False),
            ]
        )
        for warnings in (False, True):
            output, errors = io.StringIO(), io.StringIO()
            arguments = ["books.py", "list", "--for", "build", "--format", "json"]
            if warnings:
                arguments.append("--warnings")
            with (
                patch.object(sys, "argv", arguments),
                patch.object(
                    books_cli,
                    "load_manifest",
                    side_effect=lambda: load_manifest(path, root),
                ),
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(errors),
            ):
                self.assertEqual(books_cli.main(), 0)
            self.assertEqual(json.loads(output.getvalue()), {"book": ["alpha"]})
            self.assertEqual("draft but release=true" in errors.getvalue(), warnings)

    def test_list_with_warnings_rejects_invalid_manifest_without_targets(self):
        root, path = self.make_repository([self.base("alpha", status="unknown")])
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.object(
                sys, "argv", ["books.py", "list", "--for", "build", "--warnings"]
            ),
            patch.object(
                books_cli,
                "load_manifest",
                side_effect=lambda: load_manifest(path, root),
            ),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            self.assertEqual(books_cli.main(), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("invalid status", errors.getvalue())

    def base(self, slug: str, **overrides: object) -> dict:
        record = {
            "slug": slug,
            "title": slug.title(),
            "version": "1.0.0",
            "status": "draft",
            "order": 10,
        }
        record.update(overrides)
        return record

    def load(self, root: Path, path: Path) -> dict:
        return books_module.load_manifest(path, root)

    def test_site_filter_and_order_then_slug(self) -> None:
        records = [
            self.base("zeta", order=20, site=False),
            self.base("beta", order=10, site=True),
            self.base("alpha", order=10, site=True),
        ]
        root, path = self.make_repository(records)
        manifest = self.load(root, path)
        self.assertEqual(
            [book["slug"] for book in manifest["books"]], ["alpha", "beta", "zeta"]
        )

    def test_unknown_status_is_rejected(self) -> None:
        root, path = self.make_repository([self.base("alpha", status="unknown")])
        with self.assertRaisesRegex(ValueError, "invalid status"):
            self.load(root, path)


class SiteManifestValidationTests(unittest.TestCase):
    def load(self, *, defaults_build: bool = True, build=None, site=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            book_dir = root / "books" / "alpha"
            book_dir.mkdir(parents=True)
            (book_dir / "book.tex").write_text("", encoding="utf-8")
            record = {
                "slug": "alpha",
                "title": "Alpha",
                "version": "1.0.0",
                "status": "draft",
                "order": 10,
                "site": site,
            }
            if build is not None:
                record["build"] = build
            manifest = {
                "schema_version": 1,
                "defaults": {
                    "author": "Sample Author",
                    "build": defaults_build,
                    "check": True,
                    "release": False,
                    "site": False,
                },
                "books": [record],
            }
            path = root / "config/books.yml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            return load_manifest(path, root)

    def test_site_and_build_true_succeeds(self):
        manifest = self.load(build=True, site=True)
        self.assertTrue(manifest["books"][0]["build"])
        self.assertTrue(manifest["books"][0]["site"])

    def test_site_and_build_false_succeeds_when_site_is_false(self):
        self.load(build=False, site=False)

    def test_site_true_and_build_false_fails(self):
        with self.assertRaisesRegex(
            ValueError, "book 'alpha' cannot have site=true when build=false"
        ):
            self.load(build=False, site=True)

    def test_default_build_false_and_site_true_fails(self):
        with self.assertRaisesRegex(ValueError, "site=true when build=false"):
            self.load(defaults_build=False, site=True)

    def test_book_can_override_default_build_for_site(self):
        manifest = self.load(defaults_build=False, build=True, site=True)
        self.assertTrue(manifest["books"][0]["build"])
        self.assertTrue(manifest["books"][0]["site"])


if __name__ == "__main__":
    unittest.main()
