"""Exercise conservative Lean selection against real Git revisions."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


class CheckScopeTests(unittest.TestCase):
    def scope(self, path: str, before: str, after: str, *, base="HEAD~1") -> str:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = {
                **os.environ,
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            }

            def git(*arguments):
                subprocess.run(
                    ["git", *arguments],
                    cwd=root,
                    env=environment,
                    check=True,
                    capture_output=True,
                )

            git("init")
            source = root / path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(before)
            git("add", ".")
            git("commit", "-m", "baseline")
            source.write_text(after)
            git("add", ".")
            git("commit", "-m", "update")
            result = subprocess.run(
                ["python3", ROOT / "scripts/ci_check_scope.py", "--base", base],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout

    def test_pins_do_not_recompile_proofs(self):
        for path in ("config/container-image.txt", ".devcontainer/devcontainer.json"):
            with self.subTest(path=path):
                self.assertEqual(self.scope(path, "old\n", "new\n"), "lean=false\n")

    def test_artifact_updates_skip_lean_but_other_workflow_edits_do_not(self):
        before = "      - uses: actions/upload-artifact@" + "a" * 40 + " # v7\n"
        after = "      - uses: actions/upload-artifact@" + "b" * 40 + " # v7.1\n"
        path = ".github/workflows/build.yml"
        self.assertEqual(self.scope(path, before, after), "lean=false\n")
        self.assertEqual(
            self.scope(path, before, after + "        run: ashaiy lean check\n"),
            "lean=true\n",
        )
        self.assertEqual(
            self.scope(path, before.replace("upload-artifact", "checkout"), after),
            "lean=true\n",
        )

    def test_site_and_python_test_changes_skip_lean(self):
        for path in (
            "site/assets/common.css",
            "scripts/site_pages.py",
            "scripts/lean_coverage.py",
            "scripts/stage_site_pdfs.py",
            "tests/test_proof_links.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.scope(path, "old\n", "new\n"), "lean=false\n")

    def test_unknown_and_toolchain_changes_keep_lean(self):
        for path in (
            ".devcontainer/Dockerfile",
            "config/toolchain.env",
            "lean/Textbooks/Example.lean",
            "books/example/section.tex",
            "scripts/new-check.py",
            "scripts/check_proof_links.py",
            "scripts/lean_source.py",
            "books/example/chapters/topic/proofs.yml",
            "tests/fixtures/proof.lean",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.scope(path, "old\n", "new\n"), "lean=true\n")

    def test_documentation_only_change_skips_lean(self):
        self.assertEqual(
            self.scope("docs/maintainer-guide.md", "old\n", "new\n"), "lean=false\n"
        )

    def test_missing_base_keeps_lean(self):
        self.assertEqual(
            self.scope("config/container-image.txt", "old\n", "new\n", base=""),
            "lean=true\n",
        )

    def test_registry_check_and_publication_share_the_content_lock(self):
        wrapper = yaml.safe_load(
            (ROOT / ".github/workflows/prepare-image.yml").read_text()
        )
        locked = yaml.safe_load(
            (ROOT / ".github/workflows/build-toolchain.yml").read_text()
        )
        self.assertNotIn("concurrency", wrapper)
        self.assertEqual(
            wrapper["jobs"]["image"]["with"]["tag"],
            "${{ needs.inputs.outputs.tag }}",
        )
        self.assertEqual(
            locked["concurrency"],
            {
                "group": "toolchain-image-${{ inputs.tag }}",
                "cancel-in-progress": False,
                "queue": "max",
            },
        )
        self.assertEqual(locked["jobs"]["build"]["needs"], "prepare")
        self.assertIn("build", locked["jobs"]["publish"]["needs"])


if __name__ == "__main__":
    unittest.main()
