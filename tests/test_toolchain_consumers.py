"""Image preparation dependencies and execution of tested toolchain images."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from test_support import write_executable
from workflow_support import build_workflow, condition_allows

ROOT = Path(__file__).resolve().parent.parent


class ToolchainConsumerTests(unittest.TestCase):
    def test_main_prepares_images_before_selecting_consumers(self):
        jobs = build_workflow()["jobs"]
        main = jobs["main-image"]
        self.assertEqual(main["uses"], "./.github/workflows/prepare-image.yml")
        self.assertEqual(main["permissions"]["packages"], "write")
        for event, ref, expected in (
            ("push", "refs/heads/main", True),
            ("workflow_dispatch", "refs/heads/main", True),
            ("pull_request", "refs/pull/1/merge", False),
            ("workflow_dispatch", "refs/heads/topic", False),
        ):
            with self.subTest(event=event, ref=ref):
                self.assertEqual(
                    condition_allows(
                        main["if"], {"github.event_name": event, "github.ref": ref}
                    ),
                    expected,
                )
        self.assertIn("main-image", jobs["prepare-image"]["needs"])
        self.assertIn("image-validation", jobs["prepare-image"]["needs"])

    def test_failed_preparation_cannot_fall_back_to_an_old_image(self):
        condition = build_workflow()["jobs"]["prepare-image"]["if"]
        for candidate, main, expected in (
            ("success", "skipped", True),
            ("skipped", "success", True),
            ("skipped", "skipped", True),
            ("failure", "skipped", False),
            ("skipped", "failure", False),
            ("cancelled", "skipped", False),
        ):
            with self.subTest(candidate=candidate, main=main):
                self.assertEqual(
                    condition_allows(
                        condition,
                        {
                            "needs.source.result": "success",
                            "needs.image-validation.result": candidate,
                            "needs.main-image.result": main,
                        },
                    ),
                    expected,
                )

    def test_prepared_image_selection_does_not_read_the_old_pin(self):
        steps = build_workflow()["jobs"]["prepare-image"]["steps"]
        script = next(step["run"] for step in steps if step.get("id") == "image")
        for artifact in ("", "toolchain-image-amd64"):
            with self.subTest(artifact=artifact), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                output = root / "output"
                image = "ghcr.io/example/toolchain:test"
                digest = "a" * 64
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", script],
                    cwd=root,
                    env={
                        **os.environ,
                        "GITHUB_OUTPUT": str(output),
                        "PREPARED_IMAGE": image,
                        "PREPARED_DIGEST": digest,
                        "PREPARED_ARTIFACT": artifact,
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    output.read_text(),
                    f"image={image}\ndigest={digest}\nartifact={artifact}\n",
                )

    def test_consumers_receive_candidate_identity_and_skip_registry_pdf_recording(self):
        jobs = build_workflow()["jobs"]
        for name in ("latex", "book"):
            job = jobs[name]
            self.assertIn("!cancelled()", job["if"])
            for step in job["steps"]:
                if step.get("uses") != "./.github/actions/run-toolchain":
                    continue
                for key in ("image", "digest", "artifact"):
                    self.assertEqual(
                        step["with"][key],
                        "${{ needs.prepare-image.outputs." + key + " }}",
                    )
            self.assertEqual(job["permissions"]["packages"], "read")
        for step in jobs["book"]["steps"]:
            if step.get("name") in (
                "Record the verified build",
                "Upload verified build for reuse after merge",
            ):
                self.assertIn("needs.prepare-image.outputs.artifact == ''", step["if"])

    def test_local_images_run_without_a_registry_pull(self):
        action = yaml.safe_load(
            (ROOT / ".github/actions/run-toolchain/action.yml").read_text()
        )
        script = action["runs"]["steps"][-1]["run"]
        for artifact in ("", "toolchain-image-amd64"):
            with self.subTest(artifact=artifact), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                calls = root / "calls"
                write_executable(
                    root / "docker",
                    '#!/bin/sh\nprintf "%s\\n" "$*" >> "$DOCKER_CALLS"\n',
                )
                digest = "a" * 64
                image = "ghcr.io/example/toolchain"
                image += ":candidate" if artifact else f"@sha256:{digest}"
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", script],
                    env={
                        **os.environ,
                        "PATH": f"{root}:{os.environ['PATH']}",
                        "DOCKER_CALLS": str(calls),
                        "GITHUB_WORKSPACE": str(root),
                        "TOOLCHAIN_IMAGE": image,
                        "TOOLCHAIN_DIGEST": digest,
                        "TOOLCHAIN_ARTIFACT": artifact,
                        "TOOLCHAIN_COMMANDS": "ashaiy book build --check --strict",
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                commands = calls.read_text()
                self.assertEqual("pull " in commands, not bool(artifact))
                self.assertIn("--pull=never", commands)
                self.assertIn("ashaiy book build --check --strict", commands)


if __name__ == "__main__":
    unittest.main()
