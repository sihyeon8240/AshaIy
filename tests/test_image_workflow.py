"""Image selection, build isolation, and publication gates."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from test_support import write_executable
from workflow_support import build_workflow, condition_allows

ROOT = Path(__file__).resolve().parent.parent


class ImageWorkflowTests(unittest.TestCase):
    def run_image(
        self,
        event: str,
        *,
        tag_exists: bool,
        inputs_changed: bool,
        manifest=None,
        require_image=False,
        errors=(),
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            (root / "git").write_text(
                """#!/usr/bin/env bash
if [[ "$1" == cat-file ]]; then exit 0; fi
if [[ "$1" == diff ]]; then
  [[ "${INPUTS_CHANGED:-false}" == true ]] && exit 1
  exit 0
fi
exit 2
""",
                encoding="utf-8",
            )
            (root / "docker").write_text(
                """#!/usr/bin/env bash
attempt="$(cat "$ATTEMPTS" 2>/dev/null || echo 0)"
attempt=$((attempt + 1))
echo "$attempt" > "$ATTEMPTS"
error="$(sed -n "${attempt}p" "$ERRORS")"
if [[ -n "$error" ]]; then
  echo "$error" >&2
  exit 1
fi
if [[ "${TAG_EXISTS:-false}" != true ]]; then
  echo 'no such manifest: ghcr.io/example/latex:immutable' >&2
  exit 1
fi
printf '%s\\n' "$MANIFEST"
""",
                encoding="utf-8",
            )
            (root / "errors").write_text("\n".join(errors) + "\n")
            write_executable(root / "sleep", "#!/bin/sh\nexit 0\n")
            (root / "git").chmod(0o755)
            (root / "docker").chmod(0o755)
            env = {
                **os.environ,
                "GITHUB_OUTPUT": str(output),
                "ATTEMPTS": str(root / "attempts"),
                "ERRORS": str(root / "errors"),
                "IMAGE_NAME": "ghcr.io/example/latex",
                "RELEASE_TAG": "immutable",
                "TAG_EXISTS": str(tag_exists).lower(),
                "INPUTS_CHANGED": str(inputs_changed).lower(),
                "REQUIRE_IMAGE": str(require_image).lower(),
                "MANIFEST": manifest
                if manifest is not None
                else json.dumps(
                    {
                        "manifests": [
                            {"platform": {"os": "linux", "architecture": arch}}
                            for arch in ("amd64", "arm64")
                        ]
                    }
                ),
                "PATH": f"{root}:{os.environ['PATH']}",
            }
            result = subprocess.run(
                [ROOT / "scripts/check-image-tag.sh", event, "base", "head"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            return result, output.read_text(encoding="utf-8") if output.exists() else ""

    def test_registry_errors_never_authorize_a_build(self):
        for error in (
            "registry: HTTP 503 Service Unavailable",
            "unauthorized: authentication required",
            'Get "https://ghcr.io/v2/example/latex/manifests/immutable": denied',
            "dial tcp: lookup ghcr.io: no such host",
        ):
            with self.subTest(error=error):
                result, output = self.run_image(
                    "push",
                    tag_exists=True,
                    inputs_changed=False,
                    errors=(error,) * 3,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")
                self.assertEqual(result.stderr.count(error), 3)

    def test_transient_registry_failure_can_recover(self):
        result, output = self.run_image(
            "push",
            tag_exists=True,
            inputs_changed=False,
            errors=("registry: HTTP 503 Service Unavailable",),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "exists=true\n")

    def test_queue_validation_rejects_invalid_settings(self):
        script = (ROOT / "scripts/check-actions.sh").read_text().split("root_dir=")[0]
        for queue, cancel, success in (
            ("max", False, True),
            ("max", True, False),
            ("invalid", False, False),
        ):
            with (
                self.subTest(queue=queue, cancel=cancel),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                workflows = root / ".github/workflows"
                workflows.mkdir(parents=True)
                (workflows / "test.yml").write_text(
                    yaml.safe_dump(
                        {
                            "concurrency": {
                                "queue": queue,
                                "cancel-in-progress": cancel,
                            },
                            "jobs": {},
                        }
                    )
                )
                result = subprocess.run(
                    ["bash", "-c", script],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(result.returncode == 0, success, result.stderr)

    def test_image_queue_preserves_waiting_runs(self):
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/build-toolchain.yml").read_text()
        )
        self.assertEqual(workflow["concurrency"]["queue"], "max")
        self.assertIs(workflow["concurrency"]["cancel-in-progress"], False)

    def test_main_and_pr_publishers_serialize_and_recheck_registry(self):
        main = yaml.safe_load(
            (ROOT / ".github/workflows/build-toolchain.yml").read_text()
        )["jobs"]["publish"]
        pr = yaml.safe_load((ROOT / ".github/workflows/pin-pr-image.yml").read_text())[
            "jobs"
        ]["pin"]
        self.assertEqual(main["concurrency"], pr["concurrency"])
        self.assertIs(main["concurrency"]["cancel-in-progress"], False)
        steps = main["steps"]
        registry = next(step for step in steps if step.get("id") == "registry")
        self.assertEqual(registry["run"], "./scripts/check-image-tag.sh")
        assemble = next(
            step for step in steps if "imagetools create" in step.get("run", "")
        )
        self.assertLess(steps.index(registry), steps.index(assemble))
        self.assertIn("steps.registry.outputs.exists != 'true'", assemble["if"])

    def test_new_image_tag_builds(self):
        result, output = self.run_image("push", tag_exists=False, inputs_changed=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "exists=false\n")

    def test_existing_content_tag_is_reused(self):
        result, output = self.run_image("push", tag_exists=True, inputs_changed=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "exists=true\n")

    def test_dispatch_never_overwrites_existing_tag(self):
        result, output = self.run_image(
            "workflow_dispatch", tag_exists=True, inputs_changed=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "exists=true\n")

    def test_build_image_triggers_cover_tag_and_image_inputs(self):
        wrapper = (ROOT / ".github/workflows/build-image.yml").read_text(
            encoding="utf-8"
        )
        text = (ROOT / ".github/workflows/prepare-image.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python3 scripts/image_policy.py hash", text)
        self.assertIn("scripts/image_policy.py", wrapper)
        self.assertIn("RELEASE_TAG=texlive-${input_hash}", text)
        self.assertNotIn("pull_request_target:", wrapper)
        self.assertIn("workflow_dispatch:", wrapper)
        self.assertIn(
            "if: needs.prepare.outputs.exists != 'true'",
            (ROOT / ".github/workflows/build-toolchain.yml").read_text(),
        )
        self.assertNotIn("pull-requests: write", wrapper)
        self.assertIn("prepare-image.yml", wrapper)

    def test_image_builds_and_publication_are_gated(self):
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/build-toolchain.yml").read_text(encoding="utf-8")
        )
        jobs = workflow["jobs"]
        self.assertEqual(jobs["build"]["needs"], "prepare")
        self.assertEqual(jobs["build"]["if"], "needs.prepare.outputs.exists != 'true'")
        self.assertEqual(
            jobs["build"]["strategy"]["matrix"],
            "${{ fromJSON(needs.prepare.outputs.matrix) }}",
        )
        self.assertEqual(
            jobs["prepare"]["outputs"]["matrix"], "${{ steps.policy.outputs.matrix }}"
        )
        steps = jobs["build"]["steps"]
        build = next(
            step
            for step in steps
            if step.get("name") == "Build image for smoke testing"
        )
        self.assertEqual(build["with"]["platforms"], "linux/${{ matrix.arch }}")
        names = [step.get("name") for step in steps]
        self.assertLess(
            names.index("Smoke test the image toolchain"),
            names.index("Push the tested image and record its digest"),
        )
        self.assertEqual(jobs["publish"]["needs"], ["prepare", "build"])
        self.assertIn("needs.build.result == 'success'", jobs["publish"]["if"])
        self.assertIn("needs.prepare.outputs.exists == 'true'", jobs["publish"]["if"])
        self.assertIn("!cancelled()", jobs["publish"]["if"])

    def test_publishers_authenticate_before_registry_checks(self):
        jobs = yaml.safe_load(
            (ROOT / ".github/workflows/build-toolchain.yml").read_text()
        )["jobs"]
        for job_name, check_id in (("prepare", "release-tag"), ("publish", "registry")):
            with self.subTest(job=job_name):
                steps = jobs[job_name]["steps"]
                login = next(
                    step for step in steps if "login-action@" in step.get("uses", "")
                )
                check = next(step for step in steps if step.get("id") == check_id)
                self.assertLess(steps.index(login), steps.index(check))
                self.assertEqual(
                    login["with"]["password"], "${{ secrets.GITHUB_TOKEN }}"
                )
                for event in ("push", "workflow_dispatch", "pull_request"):
                    for head_repository in ("owner/repo", "contributor/fork"):
                        self.assertEqual(
                            condition_allows(
                                login["if"],
                                {
                                    "github.event_name": event,
                                    "github.repository": "owner/repo",
                                    "github.event.pull_request.head.repo.full_name": head_repository,
                                },
                            ),
                            event != "pull_request" or head_repository == "owner/repo",
                        )

    def test_denied_lookup_reports_recovery_without_authorizing_build(self):
        for required in (True, False):
            with self.subTest(required=required):
                result, output = self.run_image(
                    "push",
                    tag_exists=False,
                    inputs_changed=True,
                    require_image=required,
                    errors=("denied: requested access to the resource is denied",) * 3,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")
                self.assertIn("consumers require a public image", result.stderr)
                self.assertIn("initial publication and pin recovery", result.stderr)

    def test_pr_images_do_not_publish(self):
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/build-toolchain.yml").read_text()
        )
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if "docker push" in step.get(
                    "run", ""
                ) or "imagetools create" in step.get("run", ""):
                    with self.subTest(step=step.get("name")):
                        self.assertIn("github.event_name != 'pull_request'", step["if"])
        build_steps = workflow["jobs"]["build"]["steps"]
        archive = next(
            step for step in build_steps if "docker save" in step.get("run", "")
        )
        self.assertIn("github.event_name == 'pull_request'", archive["if"])
        self.assertNotIn("matrix.arch", archive["if"])
        for name in ("latex", "book"):
            steps = build_workflow()["jobs"][name]["steps"]
            self.assertTrue(
                any(
                    step.get("uses") == "./.github/actions/run-toolchain"
                    for step in steps
                )
            )

    def test_run_local_image_selection_does_not_access_the_registry(self):
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/build-toolchain.yml").read_text()
        )
        script = next(
            step["run"]
            for step in workflow["jobs"]["publish"]["steps"]
            if step.get("id") == "image"
        )
        for digest, success in (("sha256:" + "a" * 64, True), ("invalid", False)):
            with (
                self.subTest(digest=digest),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                (root / "build/image-digests").mkdir(parents=True)
                (root / "build/image-digests/amd64").write_text(digest + "\n")
                docker = root / "docker"
                write_executable(docker, "#!/bin/sh\nexit 99\n")
                output = root / "output"
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", script],
                    cwd=root,
                    env={
                        **os.environ,
                        "PATH": f"{root}:{os.environ['PATH']}",
                        "GITHUB_EVENT_NAME": "pull_request",
                        "GITHUB_OUTPUT": str(output),
                        "GITHUB_RUN_ID": "123",
                        "GITHUB_RUN_ATTEMPT": "2",
                        "IMAGE_NAME": "ghcr.io/example/toolchain",
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(result.returncode == 0, success, result.stderr)
                if success:
                    self.assertEqual(
                        output.read_text(),
                        f"digest={'a' * 64}\n"
                        "reference=ghcr.io/example/toolchain:build-123-2-amd64\n",
                    )
                else:
                    self.assertFalse(output.exists())

    def test_loaded_image_must_match_identity_and_architecture(self):
        action = yaml.safe_load(
            (ROOT / ".github/actions/load-toolchain/action.yml").read_text()
        )
        script = action["runs"]["steps"][-1]["run"]
        for image_id, arch, success in (
            ("sha256:" + "a" * 64, "amd64", True),
            ("sha256:" + "b" * 64, "amd64", False),
            ("sha256:" + "a" * 64, "arm64", False),
        ):
            with self.subTest(image=image_id, arch=arch):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    archive = root / "image.tar.gz"
                    archive.touch()
                    docker = root / "docker"
                    write_executable(
                        docker,
                        "#!/usr/bin/env bash\n"
                        'if [[ "$1" == load ]]; then exit 0; fi\n'
                        'case "$5" in\n'
                        "  '{{.Id}}') echo \"$IMAGE_ID\" ;;\n"
                        "  '{{.Architecture}}') echo \"$IMAGE_ARCH\" ;;\n"
                        "  *) exit 2 ;;\n"
                        "esac\n",
                    )
                    result = subprocess.run(
                        ["bash", "-euo", "pipefail", "-c", script],
                        env={
                            **os.environ,
                            "PATH": f"{root}:{os.environ['PATH']}",
                            "ARCHIVE": str(archive),
                            "IMAGE": "ghcr.io/example/toolchain:local",
                            "DIGEST": "a" * 64,
                            "IMAGE_ID": image_id,
                            "IMAGE_ARCH": arch,
                        },
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode == 0, success, result.stderr)
                    self.assertEqual(archive.exists(), not success)

    def test_image_pin_requires_successful_pr_and_trusted_publication_code(self):
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/pin-pr-image.yml").read_text()
        )
        job = workflow["jobs"]["pin"]
        self.assertIn("workflow_run.event == 'pull_request'", job["if"])
        self.assertIn("workflow_run.conclusion == 'success'", job["if"])
        self.assertIn("head_repository.full_name == github.repository", job["if"])
        checkout = job["steps"][0]
        self.assertEqual(checkout["with"]["ref"], "main")
        self.assertEqual(job["permissions"]["pull-requests"], "read")
        self.assertNotIn("pin-image", build_workflow()["jobs"])
        build = yaml.safe_load(
            (ROOT / ".github/workflows/build-toolchain.yml").read_text()
        )
        steps = build["jobs"]["build"]["steps"]
        names = [step.get("name") for step in steps]
        self.assertLess(
            names.index("Validate every checked textbook with the candidate"),
            names.index("Push the tested image and record its digest"),
        )
        self.assertLess(
            names.index("Smoke test the image toolchain"),
            names.index("Login to GitHub Container Registry"),
        )
        image_build = next(
            step
            for step in steps
            if step.get("name") == "Build image for smoke testing"
        )
        self.assertIn("steps.candidate.outputs.reused != 'true'", image_build["if"])

    def test_incomplete_or_invalid_existing_images_are_not_reused(self):
        manifests = [
            {},
            {"manifests": [{"platform": {"os": "linux", "architecture": "amd64"}}]},
            {"manifests": [{"platform": {"os": "linux", "architecture": "arm64"}}]},
            {
                "manifests": [
                    {"platform": {"os": "linux", "architecture": "amd64"}},
                    {"platform": {"os": "windows", "architecture": "arm64"}},
                ]
            },
        ]
        for manifest in [*(json.dumps(value) for value in manifests), "not json"]:
            with self.subTest(manifest=manifest):
                result, output = self.run_image(
                    "push", tag_exists=True, inputs_changed=False, manifest=manifest
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")
                self.assertIn("immutable tags must not be overwritten", result.stderr)

    def test_required_published_image_cannot_be_missing(self):
        result, output = self.run_image(
            "push", tag_exists=False, inputs_changed=False, require_image=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output, "")

    def test_attestation_descriptors_do_not_prevent_reuse(self):
        manifest = {
            "manifests": [
                {"platform": {"os": "linux", "architecture": "amd64"}},
                {"platform": {"os": "linux", "architecture": "arm64"}},
                {"platform": {"os": "unknown", "architecture": "unknown"}},
            ]
        }
        result, output = self.run_image(
            "push", tag_exists=True, inputs_changed=False, manifest=json.dumps(manifest)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "exists=true\n")


if __name__ == "__main__":
    unittest.main()
