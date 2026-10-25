"""Version intent and local preparation regression tests."""

import contextlib
import copy
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from scripts.release import releases
from tests.support.fixtures import git_environment

ROOT = Path(__file__).resolve().parents[2]


class ReleasePlanTests(unittest.TestCase):
    def setUp(self):
        self.old: dict[str, Any] = {
            "books": [
                {"slug": "alpha", "version": "1.0.0", "release": True, "build": True}
            ]
        }
        self.new = copy.deepcopy(self.old)

    def test_content_alone_does_not_release_but_enablement_does(self):
        self.assertEqual(releases.plan(self.old, self.new), [])
        self.old["books"][0]["release"] = False
        self.assertEqual(releases.plan(self.old, self.new), ["alpha"])
        self.assertEqual(releases.plan({"books": []}, self.new), ["alpha"])

    def test_first_push_plans_releases_without_reading_a_previous_commit(self):
        self.new["books"].append(
            {"slug": "beta", "version": "1.0.0", "release": False, "build": True}
        )
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                self.new["books"][0]["release"] = enabled
                output = io.StringIO()
                with (
                    patch.object(
                        sys, "argv", ["release/releases.py", "plan", "--base", "0" * 40]
                    ),
                    patch.object(releases, "load_manifest", return_value=self.new),
                    patch.object(releases.subprocess, "check_output") as git_show,
                    contextlib.redirect_stdout(output),
                ):
                    self.assertEqual(releases.main(), 0)

                git_show.assert_not_called()
                expected = (
                    'matrix={"book":["alpha"]}\ncount=1\n'
                    if enabled
                    else 'matrix={"book":[]}\ncount=0\n'
                )
                self.assertEqual(output.getvalue(), expected)

    def test_invalid_nonzero_base_is_still_rejected(self):
        error = subprocess.CalledProcessError(128, ["git", "show"])
        with (
            patch.object(
                sys, "argv", ["release/releases.py", "plan", "--base", "missing"]
            ),
            patch.object(releases.subprocess, "check_output", side_effect=error),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(releases.main(), 2)

    def test_enablement_respects_historical_defaults(self):
        del self.old["books"][0]["release"]
        self.assertEqual(releases.plan(self.old, self.new), ["alpha"])
        self.old["defaults"] = {"release": True}
        self.assertEqual(releases.plan(self.old, self.new), [])
        self.old["defaults"]["release"] = False
        self.assertEqual(releases.plan(self.old, self.new), ["alpha"])

    def test_disabling_and_remaining_disabled_never_publish(self):
        self.new["books"][0]["release"] = False
        self.assertEqual(releases.plan(self.old, self.new), [])
        self.old["books"][0]["release"] = False
        self.assertEqual(releases.plan(self.old, self.new), [])

    def test_enablement_still_rejects_regression_or_disabled_build(self):
        self.old["books"][0]["release"] = False
        self.new["books"][0]["build"] = False
        with self.assertRaises(ValueError):
            releases.plan(self.old, self.new)
        self.new["books"][0].update(build=True, version="0.9.0")
        with self.assertRaises(ValueError):
            releases.plan(self.old, self.new)

    def test_version_increase_selects_only_eligible_books(self):
        self.new["books"][0]["version"] = "1.1.0"
        self.assertEqual(releases.plan(self.old, self.new), ["alpha"])
        self.new["books"][0]["release"] = False
        self.assertEqual(releases.plan(self.old, self.new), [])

    def test_multiple_books_are_selected_independently(self):
        self.old["books"].append({**self.old["books"][0], "slug": "beta"})
        self.new = copy.deepcopy(self.old)
        for book in self.new["books"]:
            book["version"] = "2.0.0"
        self.assertEqual(releases.plan(self.old, self.new), ["alpha", "beta"])

    def test_regression_and_disabled_build_fail(self):
        for version, build in [("0.9.0", True), ("1.1.0", False)]:
            with self.subTest(version=version):
                self.new["books"][0].update(version=version, build=build)
                with self.assertRaises(ValueError):
                    releases.plan(self.old, self.new)

    def test_semver_prerelease_precedence(self):
        ordered = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-beta",
            "1.0.0-rc.2",
            "1.0.0-rc.10",
            "1.0.0",
            "1.0.1",
        ]
        self.assertEqual(sorted(reversed(ordered), key=releases.version_key), ordered)
        for invalid in ["01.0.0", "1.0", "1.0.0-01", "1.0.0;echo bad"]:
            with self.assertRaises(ValueError):
                releases.version_key(invalid)

    def test_remote_tags_reject_existing_versions_and_propagate_lookup_errors(self):
        ref = "refs/tags/alpha-v1.0.0"
        with patch.object(releases.subprocess, "check_output", return_value="") as git:
            releases.check_remote_tags(["alpha"], self.new)
            self.assertEqual(
                git.call_args.args[0], ["git", "ls-remote", "--refs", "origin", ref]
            )
        with (
            patch.object(
                releases.subprocess, "check_output", return_value=f"{'a' * 40}\t{ref}\n"
            ),
            self.assertRaisesRegex(ValueError, "alpha-v1.0.0"),
        ):
            releases.check_remote_tags(["alpha"], self.new)
        with (
            patch.object(
                releases.subprocess,
                "check_output",
                side_effect=subprocess.CalledProcessError(128, ["git", "ls-remote"]),
            ),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            releases.check_remote_tags(["alpha"], self.new)
        with patch.object(releases.subprocess, "check_output") as git:
            releases.check_remote_tags([], self.new)
            git.assert_not_called()

    def test_remote_tag_lookup_uses_live_remote_for_both_tag_types(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            local = root / "local"
            environment = git_environment()

            def git(*args):
                subprocess.run(
                    ["git", *args],
                    env=environment,
                    check=True,
                    capture_output=True,
                    timeout=10,
                )

            git("init", "--bare", str(remote))
            git("init", str(local))
            git("-C", str(local), "config", "user.name", "Test")
            git("-C", str(local), "config", "user.email", "test@example.invalid")
            git("-C", str(local), "commit", "--allow-empty", "-m", "Initial")
            git("-C", str(local), "remote", "add", "origin", str(remote))
            for annotated in (False, True):
                with self.subTest(annotated=annotated):
                    tag = "alpha-v1.0.0"
                    options = ["-a", "-m", "Release"] if annotated else []
                    git("-C", str(local), "tag", *options, tag)
                    git("-C", str(local), "push", "origin", f"refs/tags/{tag}")
                    git("-C", str(local), "tag", "-d", tag)
                    with (
                        patch.object(releases, "ROOT", local),
                        self.assertRaisesRegex(ValueError, tag),
                    ):
                        releases.check_remote_tags(["alpha"], self.new)
                    git("-C", str(local), "push", "origin", f":refs/tags/{tag}")
            with patch.object(releases, "ROOT", local):
                releases.check_remote_tags(["alpha"], self.new)

    def test_summary_lists_only_selected_releases_and_explains_empty_plan(self):
        self.new["books"].append(
            {"slug": "beta", "version": "2.0.0", "release": False, "build": True}
        )
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / "summary.md"
            summary.write_text("Existing summary\n")
            releases.report_plan(["alpha"], self.new, summary)
            text = summary.read_text()
            self.assertTrue(text.startswith("Existing summary\n"))
            self.assertIn("alpha | 1.0.0 | `alpha-v1.0.0`", text)
            self.assertNotIn("beta", text)
            releases.report_plan([], self.new, summary)
            self.assertIn("No textbook releases planned.", summary.read_text())

    def test_prepare_preserves_manifest_comments_and_updates_assembly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = (
                "# keep this comment\n"
                "books:\n"
                "  - slug: alpha\n"
                "    version: '1.0.0' # keep this too\n"
            )
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config/books.yml").write_text(source)
            generated = root / "book.tex"
            generated.write_text("old assembly")
            with (
                patch.object(releases, "ROOT", root),
                patch.object(releases, "load_manifest", return_value=self.old),
                patch.object(
                    releases.subprocess, "check_output", return_value="local-work\n"
                ),
                patch.object(
                    releases, "expected_files", return_value={generated: "new assembly"}
                ) as expected,
            ):
                releases.prepare("alpha", "1.1.0")
            self.assertEqual(
                (root / "config/books.yml").read_text(),
                source.replace(
                    "    version:", "    release: true\n    version:"
                ).replace("'1.0.0'", "1.1.0"),
            )
            self.assertEqual(generated.read_text(), "new assembly")
            self.assertEqual(expected.call_args.kwargs["book"]["version"], "1.1.0")

    def test_prepare_enables_current_version_with_explicit_or_inherited_flag(self):
        self.old["books"][0]["release"] = False
        for field in ["    release: false # retain comment\n", ""]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = "books:\n  - slug: alpha\n" + field + "    version: 1.0.0\n"
                (root / "config").mkdir(parents=True, exist_ok=True)
                (root / "config/books.yml").write_text(source)
                with (
                    patch.object(releases, "ROOT", root),
                    patch.object(releases, "load_manifest", return_value=self.old),
                    patch.object(
                        releases.subprocess, "check_output", return_value="local-work\n"
                    ),
                    patch.object(
                        releases, "expected_files", return_value={}
                    ) as expected,
                ):
                    releases.prepare("alpha", "1.0.0")
                result = (root / "config/books.yml").read_text()
                self.assertIn("release: true", result)
                self.assertIn("version: 1.0.0", result)
                if field:
                    self.assertIn("# retain comment", result)
                self.assertTrue(expected.call_args.kwargs["book"]["release"])

    def test_prepare_inherited_version_preserves_other_books_and_generates_assembly(
        self,
    ):
        from scripts.books.book_manifest import load_manifest
        from tests.support.fixtures import book_record, manifest_document, write_yaml

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = [book_record("alpha"), book_record("beta", order=20)]
            for record in records:
                del record["version"]
                entry = root / "books" / record["slug"] / "book.tex"
                entry.parent.mkdir(parents=True)
                entry.write_text("old assembly\n")
            path = root / "config/books.yml"
            write_yaml(path, manifest_document(records, version="1.0.0"))
            source = path.read_text().replace("version: 1.0.0", "version: 1.0.0 # keep")
            path.write_text(source)
            book = root / "books/alpha"
            write_yaml(
                book / "chapters.yml",
                {
                    "schema_version": 1,
                    "chapters": [{"slug": "start", "title": "Start"}],
                },
            )
            write_yaml(
                book / "chapters/start/sections.yml",
                {
                    "schema_version": 1,
                    "sections": [{"slug": "first", "title": "First"}],
                },
            )
            (book / "chapters/start/first.tex").write_text("%\n")
            with (
                patch.object(releases, "ROOT", root),
                patch.object(
                    releases,
                    "load_manifest",
                    side_effect=lambda: load_manifest(path, root),
                ),
                patch.object(
                    releases.subprocess, "check_output", return_value="local-work\n"
                ),
            ):
                releases.prepare("alpha", "1.1.0")
            manifest = load_manifest(path, root)
            self.assertEqual(
                [item["version"] for item in manifest["books"]], ["1.1.0", "1.0.0"]
            )
            self.assertEqual(
                [item["release"] for item in manifest["books"]], [True, False]
            )
            self.assertIn("version: 1.0.0 # keep", path.read_text())
            self.assertIn(
                r"\newcommand{\version}{1.1.0}", (book / "book.tex").read_text()
            )

    def test_flow_mapping_edits_preserve_comments_and_trailing_commas(self):
        import yaml

        for fields in (
            "slug: alpha, title: Alpha",
            "slug: alpha, title: Alpha,",
            "slug: alpha, title: Alpha, # keep this comment\n",
            "slug: alpha, version: 1.0.0,",
            "slug: alpha, version: 1.0.0, release: false,",
        ):
            source = "{" + fields + "}"
            with self.subTest(source=source):
                updated = source
                for start, end, replacement in sorted(
                    releases.release_edits(source, yaml.compose(source), "1.1.0"),
                    reverse=True,
                ):
                    updated = updated[:start] + replacement + updated[end:]
                data = yaml.safe_load(updated)
                self.assertEqual(data["version"], "1.1.0")
                self.assertIs(data["release"], True)
                self.assertEqual(data["slug"], "alpha")
                self.assertEqual(
                    source.count("# keep this comment"),
                    updated.count("# keep this comment"),
                )
                self.assertIn("slug: alpha", updated)
                if "title" in fields:
                    self.assertIn("title: Alpha,", updated)

    def test_prepare_rejects_main_detached_disabled_and_nonincrease(self):
        for branch in ["main\n", "\n"]:
            with (
                patch.object(releases.subprocess, "check_output", return_value=branch),
                self.assertRaises(ValueError),
            ):
                releases.prepare("alpha", "1.1.0")
        with (
            patch.object(
                releases.subprocess, "check_output", return_value="local-work\n"
            ),
            patch.object(releases, "load_manifest", return_value=self.old),
        ):
            with self.assertRaises(ValueError):
                releases.prepare("alpha", "1.0.0")
            self.old["books"][0]["build"] = False
            with self.assertRaises(ValueError):
                releases.prepare("alpha", "1.1.0")


if __name__ == "__main__":
    unittest.main()
