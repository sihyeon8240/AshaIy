"""PDF snapshot updates, publication gates, and Pages sources."""

from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from test_support import (
    book_record,
    copy_validation_configuration,
    manifest_document,
    write_executable,
    write_yaml,
)
from workflow_support import build_workflow, condition_allows

ROOT = Path(__file__).resolve().parent.parent


class SnapshotWorkflowTests(unittest.TestCase):
    def test_pages_guard_distinguishes_superseded_snapshots_from_git_failures(self):
        selected = "a" * 40
        cases = (
            ({}, 0, "current=true\n"),
            ({"REMOTE_SHA": "b" * 40}, 0, "current=false\n"),
            ({"FETCH_STATUS": "7"}, 7, ""),
            ({"REV_PARSE_STATUS": "9"}, 9, ""),
            ({"SNAPSHOT_SHA": "invalid"}, 1, ""),
        )
        for values, status, expected in cases:
            with (
                self.subTest(values=values),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                output = root / "output"
                write_executable(
                    root / "git",
                    """#!/usr/bin/env bash
case "$1" in
  fetch) exit "${FETCH_STATUS:-0}" ;;
  rev-parse)
    printf '%s\\n' "${REMOTE_SHA}"
    exit "${REV_PARSE_STATUS:-0}"
    ;;
  *) exit 2 ;;
esac
""",
                )
                result = subprocess.run(
                    [ROOT / "scripts/pages_current.sh"],
                    env={
                        **os.environ,
                        "PATH": f"{root}:{os.environ['PATH']}",
                        "SNAPSHOT_SHA": selected,
                        "REMOTE_SHA": selected,
                        "GITHUB_OUTPUT": str(output),
                        **values,
                    },
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(
                    output.read_text() if output.exists() else "", expected
                )

    def run_pdf_update(
        self,
        updated: dict[str, bytes],
        existing: dict[str, bytes],
        *,
        registered=("alpha", "beta"),
        site=("alpha", "beta"),
        invalid_manifest: bool = False,
        retain_recovery: bool = False,
        environment: dict[str, str] | None = None,
        **environment_overrides: str,
    ):
        environment = {**(environment or {}), **environment_overrides}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "snapshot" / "pdf").mkdir(parents=True)
            for name, data in existing.items():
                (root / "snapshot" / "pdf" / name).write_bytes(data)
            if updated:
                (root / "updated-pdfs").mkdir()
                for name, data in updated.items():
                    (root / "updated-pdfs" / name).write_bytes(data)
            (root / "scripts").mkdir()
            shutil.copy2(
                ROOT / "scripts/publish_snapshot.sh",
                root / "scripts/publish_snapshot.sh",
            )
            (root / ".github").mkdir()
            (root / ".github/generated-pdfs-README.md").write_text("Snapshot\n")
            binary = root / "bin"
            binary.mkdir()
            write_executable(
                binary / "git",
                """#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path
args = sys.argv[1:]
root = Path(os.environ["FIXTURE"])
with open(os.environ["GIT_LOG"], "a") as log:
    log.write(" ".join(args) + "\\n")
if args == ["rev-parse", "origin/main"]:
    if os.environ.get("MAIN_LOOKUP_STATUS"):
        raise SystemExit(int(os.environ["MAIN_LOOKUP_STATUS"]))
    counter = root / "main-lookups"
    count = int(counter.read_text()) + 1 if counter.exists() else 1
    counter.write_text(str(count))
    print(os.environ.get("LATE_REMOTE_SHA" if count > 1 else "REMOTE_SHA", os.environ["GITHUB_SHA"]))
elif args == ["fetch", "--no-tags", "origin", "main"]:
    raise SystemExit(int(os.environ.get("FETCH_MAIN_STATUS", "0")))
elif args[:2] == ["ls-remote", "--exit-code"]:
    raise SystemExit(int(os.environ.get("LS_REMOTE_STATUS", "0")))
elif args[:2] == ["worktree", "add"]:
    shutil.copytree(root / "snapshot", args[3], dirs_exist_ok=True)
elif args[:2] == ["worktree", "remove"]:
    shutil.rmtree(root / "snapshot")
    shutil.copytree(args[3], root / "snapshot")
    shutil.rmtree(args[3])
elif "diff" in args:
    raise SystemExit(int(os.environ.get("DIFF_STATUS", "1")))
elif "push" in args:
    raise SystemExit(int(os.environ.get("PUSH_STATUS", "0")))
elif args[-2:] == ["rev-parse", "HEAD"]:
    if os.environ.get("SNAPSHOT_LOOKUP_STATUS"):
        raise SystemExit(int(os.environ["SNAPSHOT_LOOKUP_STATUS"]))
    print("c" * 40)
""",
            )
            (root / "tmp").mkdir()
            copy_validation_configuration(root)
            for name in ("snapshot_state.py", "book_manifest.py", "source_reads.py"):
                shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
            write_yaml(
                root / "config/books.yml",
                manifest_document(
                    [
                        book_record(slug, label_prefix=slug, site=slug in site)
                        for slug in registered
                    ]
                ),
            )
            for slug in registered:
                book = root / "books" / slug
                book.mkdir(parents=True)
                (book / "book.tex").write_text("test book\n")
            if invalid_manifest:
                (root / "config/books.yml").write_text("invalid: manifest\n")
            if retain_recovery:
                (root / "scripts/snapshot_state.py").write_text(
                    "import sys\nfrom pathlib import Path\n"
                    "recovery = Path(sys.argv[1]) / '.pdf-staging-test/previous'\n"
                    "recovery.mkdir(parents=True)\nraise SystemExit(1)\n"
                )
            result = subprocess.run(
                [str(root / "scripts/publish_snapshot.sh")],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
                env={
                    **os.environ,
                    "PATH": f"{binary}:{os.environ['PATH']}",
                    "GIT_LOG": str(root / "git.log"),
                    "FIXTURE": str(root),
                    "TMPDIR": str(root / "tmp"),
                    "GITHUB_SHA": "a" * 40,
                    "BUILD_PLAN": json.dumps(
                        {"book": [Path(name).stem for name in updated]}
                    ),
                    "GITHUB_OUTPUT": str(root / "output"),
                    **environment,
                },
                timeout=30,
            )
            snapshot = {
                path.name: path.read_bytes()
                for path in (root / "snapshot" / "pdf").iterdir()
            }
            output = root / "output"
            return (
                result,
                snapshot,
                {
                    "outputs": output.read_text() if output.exists() else "",
                    "git": (root / "git.log").read_text(),
                    "temporary": list((root / "tmp").iterdir()),
                },
            )

    def run_snapshot(self, **values: str):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            git = root / "git"
            write_executable(
                git,
                """#!/usr/bin/env bash
case "$1" in
  fetch) exit "${FETCH_STATUS:-0}" ;;
  show) printf '%s' "${SOURCE_SHA:-}"; exit "${SHOW_STATUS:-0}" ;;
  cat-file) exit "${COMMIT_STATUS:-0}" ;;
  merge-base) exit "${ANCESTOR_STATUS:-0}" ;;
  *) exit 2 ;;
esac
""",
            )
            env = {
                **os.environ,
                **values,
                "GITHUB_OUTPUT": str(output),
                "PATH": f"{root}:{os.environ['PATH']}",
            }
            result = subprocess.run(
                [ROOT / "scripts/snapshot_base.sh"],
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            return result, output.read_text(encoding="utf-8")

    def test_snapshot_base_valid_sha(self):
        sha = "a" * 40
        result, output = self.run_snapshot(SOURCE_SHA=sha)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, f"base={sha}\n")

    def test_snapshot_base_failures_emit_explicit_empty_base(self):
        cases = (
            {"FETCH_STATUS": "1"},
            {"SHOW_STATUS": "1"},
            {"SOURCE_SHA": "invalid"},
            {"SOURCE_SHA": "a" * 40, "COMMIT_STATUS": "1"},
            {"SOURCE_SHA": "a" * 40, "ANCESTOR_STATUS": "1"},
        )
        for values in cases:
            with self.subTest(values=values):
                result, output = self.run_snapshot(**values)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, "base=\n")

    def test_publish_condition_requires_main_changes_and_successful_gates(self):
        publish = build_workflow()["jobs"]["publish"]
        for gate in ("plan", "book", "check", "build-check"):
            self.assertIn(gate, publish["needs"])
        baseline = {
            "github.event_name": "push",
            "github.ref": "refs/heads/main",
            "needs.plan.result": "success",
            "needs.book.result": "success",
            "needs.check.result": "success",
            "needs.build-check.result": "success",
            "needs.plan.outputs.count": "1",
            "needs.plan.outputs.site_changed": "false",
            "needs.plan.outputs.snapshot_changed": "false",
        }
        self.assertTrue(condition_allows(publish["if"], baseline))
        for gate in ("plan", "book", "check", "build-check"):
            for result in ("success", "failure", "cancelled", "skipped"):
                with self.subTest(gate=gate, result=result):
                    expected = result == "success" or (
                        gate == "book" and result == "skipped"
                    )
                    self.assertEqual(
                        condition_allows(
                            publish["if"], {**baseline, f"needs.{gate}.result": result}
                        ),
                        expected,
                    )
        for event, branch, count, site, snapshot in itertools.product(
            ("push", "workflow_dispatch", "pull_request"),
            ("refs/heads/main", "refs/heads/local-work"),
            ("0", "1"),
            ("false", "true"),
            ("false", "true"),
        ):
            with self.subTest(
                event=event, branch=branch, count=count, site=site, snapshot=snapshot
            ):
                context = {
                    **baseline,
                    "github.event_name": event,
                    "github.ref": branch,
                    "needs.plan.outputs.count": count,
                    "needs.plan.outputs.site_changed": site,
                    "needs.plan.outputs.snapshot_changed": snapshot,
                }
                expected = (
                    event in {"push", "workflow_dispatch"}
                    and branch == "refs/heads/main"
                    and (count != "0" or site == "true" or snapshot == "true")
                )
                self.assertEqual(condition_allows(publish["if"], context), expected)

    def test_pages_retries_existing_snapshot_after_documentation_only_push(self):
        job = build_workflow()["jobs"]["pages"]
        baseline = {
            "github.event_name": "push",
            "github.ref": "refs/heads/main",
            "needs.check.result": "success",
            "needs.build-check.result": "success",
            "needs.publish.result": "skipped",
            "needs.publish.outputs.current": "",
        }
        self.assertTrue(condition_allows(job["if"], baseline))
        self.assertIn("needs.publish.outputs.current", job["with"]["source_sha"])
        self.assertIn("|| ''", job["with"]["source_sha"])
        for overrides in (
            {"github.event_name": "pull_request"},
            {"github.ref": "refs/heads/local-work"},
            {"needs.check.result": "failure"},
            {"needs.build-check.result": "cancelled"},
            {"needs.publish.result": "failure"},
            {
                "needs.publish.result": "success",
                "needs.publish.outputs.current": "false",
            },
            {"cancelled": True},
        ):
            with self.subTest(overrides=overrides):
                self.assertFalse(condition_allows(job["if"], {**baseline, **overrides}))
        self.assertTrue(
            condition_allows(
                job["if"],
                {
                    **baseline,
                    "needs.publish.result": "success",
                    "needs.publish.outputs.current": "true",
                },
            )
        )

    def test_pdf_update_accepts_zero_one_and_multiple_inputs(self):
        cases = (
            (
                {},
                {"alpha.pdf": b"old-a", "beta.pdf": b"old-b"},
                {"alpha.pdf": b"old-a", "beta.pdf": b"old-b"},
            ),
            (
                {"alpha.pdf": b"new-a"},
                {"beta.pdf": b"old-b"},
                {"alpha.pdf": b"new-a", "beta.pdf": b"old-b"},
            ),
            (
                {"alpha.pdf": b"new-a", "beta.pdf": b"new-b"},
                {},
                {"alpha.pdf": b"new-a", "beta.pdf": b"new-b"},
            ),
        )
        for updated, existing, expected in cases:
            with self.subTest(updated=updated):
                result, snapshot, _ = self.run_pdf_update(updated, existing)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(snapshot, expected)

    def test_missing_planned_artifact_preserves_pdfs_and_never_pushes(self):
        existing = {"alpha.pdf": b"old-a", "beta.pdf": b"old-b"}
        result, snapshot, report = self.run_pdf_update(
            {}, existing, BUILD_PLAN='{"book":["alpha"]}'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("artifacts differ from the build plan", result.stderr)
        self.assertEqual(snapshot, existing)
        self.assertNotIn("push origin", report["git"])
        self.assertEqual(report["outputs"], "")

    def test_pdf_update_prunes_files_that_are_no_longer_for_site(self):
        result, snapshot, _ = self.run_pdf_update(
            {},
            {"alpha.pdf": b"a", "retired.pdf": b"old"},
            registered=("alpha", "retired"),
            site=("alpha",),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot, {"alpha.pdf": b"a"})

    def test_pdf_update_rejects_unknown_slug(self):
        result, snapshot, _ = self.run_pdf_update(
            {"unknown.pdf": b"pdf"},
            {"alpha.pdf": b"old-a", "beta.pdf": b"old-b"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown PDF artifact slug: unknown", result.stderr)

    def test_pdf_update_rejects_empty_artifact_before_slug_validation(self):
        result, snapshot, _ = self.run_pdf_update(
            {"alpha.pdf": b""},
            {"alpha.pdf": b"old-a", "beta.pdf": b"old-b"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PDF artifact is missing or empty", result.stderr)

    def test_failed_site_selection_does_not_prune_existing_pdfs(self):
        existing = {"alpha.pdf": b"old-a", "beta.pdf": b"old-b"}
        result, snapshot, _ = self.run_pdf_update({}, existing, invalid_manifest=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(snapshot, existing)

    def test_newer_main_skips_snapshot_updates(self):
        existing = {"alpha.pdf": b"old-a", "beta.pdf": b"old-b"}
        result, snapshot, _ = self.run_pdf_update(
            {"alpha.pdf": b"new-a"}, existing, REMOTE_SHA="b" * 40
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot, existing)
        self.assertIn("A newer main commit exists", result.stdout)

    def test_incomplete_update_does_not_replace_existing_pdfs(self):
        existing = {"alpha.pdf": b"old-a"}
        result, snapshot, _ = self.run_pdf_update({"alpha.pdf": b"new-a"}, existing)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot lacks site PDF beta", result.stderr)
        self.assertEqual(snapshot, existing)

    def test_later_unknown_update_does_not_replace_valid_book(self):
        existing = {"alpha.pdf": b"old-a", "beta.pdf": b"old-b"}
        result, snapshot, _ = self.run_pdf_update(
            {"alpha.pdf": b"new-a", "unknown.pdf": b"unknown"}, existing
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(snapshot, existing)

    def test_remote_lookup_errors_do_not_bootstrap_a_snapshot(self):
        for status in (1, 128):
            with self.subTest(status=status):
                result, _, report = self.run_pdf_update(
                    {},
                    {"alpha.pdf": b"a", "beta.pdf": b"b"},
                    LS_REMOTE_STATUS=str(status),
                )
                self.assertEqual(result.returncode, status)
                self.assertNotIn("worktree add", report["git"])
                self.assertEqual(report["outputs"], "")
                self.assertEqual(report["temporary"], [])

    def test_absent_remote_ref_bootstraps_and_cleans_its_worktree(self):
        result, _, report = self.run_pdf_update(
            {"alpha.pdf": b"a", "beta.pdf": b"b"}, {}, LS_REMOTE_STATUS="2"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("switch --orphan snapshot-bootstrap-", report["git"])
        self.assertIn("current=true", report["outputs"])
        self.assertEqual(report["temporary"], [])

    def test_recovery_copy_retains_the_worktree_and_bootstrap_branch(self):
        result, _, report = self.run_pdf_update(
            {}, {}, retain_recovery=True, LS_REMOTE_STATUS="2"
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(report["temporary"]), 1)
        self.assertIn("Snapshot recovery worktree retained:", result.stderr)
        self.assertNotIn("worktree remove", report["git"])
        self.assertNotIn("update-ref -d", report["git"])
        self.assertEqual(report["outputs"], "")

    def test_diff_and_push_errors_never_emit_success(self):
        for environment in (
            {"DIFF_STATUS": "128"},
            {"PUSH_STATUS": "17"},
            {"SNAPSHOT_LOOKUP_STATUS": "128"},
        ):
            with self.subTest(environment=environment):
                result, _, report = self.run_pdf_update(
                    {}, {"alpha.pdf": b"a", "beta.pdf": b"b"}, environment=environment
                )
                self.assertEqual(
                    result.returncode, int(next(iter(environment.values())))
                )
                self.assertEqual(report["outputs"], "")
                self.assertEqual(report["temporary"], [])
                if "DIFF_STATUS" in environment:
                    self.assertNotIn("push origin", report["git"])

    def test_main_lookup_errors_do_not_emit_a_successful_skip(self):
        for environment in ({"FETCH_MAIN_STATUS": "1"}, {"MAIN_LOOKUP_STATUS": "128"}):
            with self.subTest(environment=environment):
                result, _, report = self.run_pdf_update({}, {}, environment=environment)
                self.assertEqual(
                    result.returncode, int(next(iter(environment.values())))
                )
                self.assertEqual(report["outputs"], "")
                self.assertEqual(report["temporary"], [])

    def test_main_advance_during_preparation_skips_push(self):
        result, _, report = self.run_pdf_update(
            {"alpha.pdf": b"new"},
            {"alpha.pdf": b"a", "beta.pdf": b"b"},
            LATE_REMOTE_SHA="b" * 40,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["outputs"], "current=false\n")
        self.assertNotIn("push origin", report["git"])
        self.assertEqual(report["temporary"], [])

    def test_superseded_pages_skip_all_build_upload_and_deploy_steps(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/pages.yml").read_text())
        steps = workflow["jobs"]["deploy"]["steps"]
        early = next(
            index for index, step in enumerate(steps) if step.get("id") == "eligible"
        )
        for step in steps[early + 1 :]:
            with self.subTest(step=step.get("name", step.get("uses"))):
                self.assertFalse(
                    condition_allows(
                        step["if"],
                        {
                            "steps.eligible.outputs.current": "false",
                            "steps.current.outputs.current": "",
                        },
                    )
                )

    def test_pages_requires_snapshot_source_correspondence(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/pages.yml").read_text())
        step = next(
            step
            for step in workflow["jobs"]["deploy"]["steps"]
            if step.get("id") == "source"
        )
        for snapshot_sha, call_sha, success in (
            ("a" * 40, "a" * 40, True),
            ("b" * 40, "", True),
            ("a" * 40, "b" * 40, False),
            ("invalid", "", False),
            ("", "", False),
            (None, "", False),
        ):
            with (
                self.subTest(snapshot=snapshot_sha, call=call_sha),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                output = root / "output"
                (root / "pdf-snapshot").mkdir()
                if snapshot_sha is not None:
                    (root / "pdf-snapshot/.source-sha").write_text(snapshot_sha + "\n")
                write_executable(root / "git", "#!/bin/sh\necho " + "c" * 40 + "\n")
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", step["run"]],
                    cwd=root,
                    env={
                        **os.environ,
                        "PATH": f"{root}:{os.environ['PATH']}",
                        "CALL_SHA": call_sha,
                        "GITHUB_OUTPUT": str(output),
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(result.returncode == 0, success, result.stderr)
                if success:
                    self.assertEqual(
                        output.read_text(), f"sha={snapshot_sha}\nsnapshot={'c' * 40}\n"
                    )
                else:
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
