"""PR publication provenance and exact-head, two-file pin commits."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


from scripts import image_pr

ROOT = Path(__file__).resolve().parent.parent


IMAGE = "ghcr.io/example/toolchain@sha256:" + "a" * 64


def pull_request(head: str = "head") -> dict:
    return {
        "number": 7,
        "state": "open",
        "base": {"sha": "base", "ref": "main", "repo": {"full_name": "owner/repo"}},
        "head": {"sha": head, "ref": "topic", "repo": {"full_name": "owner/repo"}},
    }


class ImagePrSelectionTests(unittest.TestCase):
    def setUp(self):
        self.workflow_run = {
            "id": 123,
            "run_attempt": 2,
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
            "head_sha": "head",
            "head_repository": {"full_name": "owner/repo"},
            "path": ".github/workflows/build.yml",
        }

    def test_only_current_open_same_repository_prs_are_selected(self):
        for field, value in (
            (None, None),
            (("state",), "closed"),
            (("head", "sha"), "new-head"),
            (("head", "ref"), "main"),
            (("head", "repo"), None),
            (("head", "repo", "full_name"), "fork/repo"),
            (("base", "ref"), "other"),
            (("base", "repo", "full_name"), "other/repo"),
        ):
            pull = pull_request()
            if field:
                target = pull
                for key in field[:-1]:
                    target = target[key]
                target[field[-1]] = value
            with (
                self.subTest(field=field),
                patch.object(
                    image_pr.github_artifacts, "api", side_effect=[[pull], pull]
                ),
            ):
                result = image_pr.select_pull("owner/repo", self.workflow_run)
                self.assertEqual(result, pull if field is None else None)

    def test_failed_fork_and_wrong_workflow_runs_never_query_prs(self):
        for key, value in (
            ("conclusion", "failure"),
            ("event", "push"),
            ("head_repository", {"full_name": "fork/repo"}),
            ("path", ".github/workflows/unrelated.yml"),
        ):
            with (
                self.subTest(key=key),
                patch.object(image_pr.github_artifacts, "api") as api,
            ):
                self.assertIsNone(
                    image_pr.select_pull(
                        "owner/repo", {**self.workflow_run, key: value}
                    )
                )
                api.assert_not_called()

    def publish(self, *, exists=False, artifacts=None, paths=None, load_error=None):
        pull = pull_request()
        artifacts = (
            artifacts
            if artifacts is not None
            else [
                {
                    "name": f"toolchain-image-{arch}",
                    "expired": False,
                    "size_in_bytes": 1,
                }
                for arch in ("amd64", "arm64")
            ]
        )
        calls = []

        def execute(*args, **kwargs):
            calls.append(args)
            if args[:3] == ("git", "show", "-s"):
                return "base head"
            if args[:2] == ("git", "rev-parse"):
                return "tree" if args[-1].endswith("^{tree}") else "merge"
            if args[:2] == ("bash", "scripts/check_image_tag.sh"):
                output = kwargs["env"].get("GITHUB_OUTPUT")
                if output:
                    Path(output).write_text(f"exists={str(exists).lower()}\n")
            if args[:4] == ("docker", "buildx", "imagetools", "inspect"):
                return "sha256:" + "a" * 64
            return ""

        load = Mock(side_effect=load_error)
        with (
            patch.dict(
                os.environ, {"GITHUB_REPOSITORY": "owner/repo", "SOURCE_RUN_ID": "123"}
            ),
            patch.object(
                image_pr.github_artifacts,
                "api",
                side_effect=[self.workflow_run, {"artifacts": artifacts}],
            ),
            patch.object(image_pr, "select_pull", return_value=pull),
            patch.object(
                image_pr,
                "source_policy",
                return_value=(
                    {
                        "inputs": [".devcontainer/Dockerfile"],
                        "platforms": [{"arch": arch} for arch in ("amd64", "arm64")],
                    },
                    "texlive-0123456789ab",
                ),
            ),
            patch.object(
                image_pr,
                "changed_paths",
                return_value=paths
                if paths is not None
                else [".devcontainer/Dockerfile"],
            ),
            patch.object(image_pr, "source_text", return_value=IMAGE + "\n"),
            patch.object(image_pr, "load_image", return_value=IMAGE),
            patch.object(image_pr, "command", side_effect=execute),
            patch.object(image_pr, "append_pin") as pin,
        ):
            error = None
            try:
                image_pr.publish(load, policy="policy", max_bytes=100)
            except ValueError as exception:
                error = exception
            return calls, load, pin, error

    def test_publication_requires_all_artifacts_and_loads_before_push(self):
        calls, load, pin, error = self.publish()
        self.assertIsNone(error)
        self.assertEqual(load.call_count, 2)
        self.assertEqual(
            load.call_args_list[0].args[2],
            {"tree": "tree", "arch": "amd64", "policy": "policy"},
        )
        self.assertEqual(
            len([call for call in calls if call[:2] == ("docker", "push")]), 2
        )
        self.assertEqual(
            len(
                [
                    call
                    for call in calls
                    if call[:4] == ("docker", "buildx", "imagetools", "create")
                ]
            ),
            1,
        )
        self.assertFalse(
            any(call[:2] in (("docker", "run"), ("git", "checkout")) for call in calls)
        )
        pin.assert_called_once_with("owner/repo", pull_request(), IMAGE)

        for artifacts in (
            [],
            [{"name": "toolchain-image-amd64", "expired": False, "size_in_bytes": 1}],
        ):
            calls, load, pin, error = self.publish(artifacts=artifacts)
            self.assertIsInstance(error, ValueError)
            load.assert_not_called()
            pin.assert_not_called()
            self.assertFalse(any(call[:2] == ("docker", "push") for call in calls))

    def test_invalid_candidate_never_publishes_index_or_pin(self):
        calls, _, pin, error = self.publish(load_error=ValueError("tree mismatch"))
        self.assertIsInstance(error, ValueError)
        pin.assert_not_called()
        self.assertFalse(any(call[:2] == ("docker", "push") for call in calls))

    def test_existing_image_retries_without_artifact_downloads(self):
        _, load, pin, error = self.publish(exists=True)
        self.assertIsNone(error)
        load.assert_not_called()
        pin.assert_called_once()

    def test_ordinary_book_pr_never_publishes_or_pins(self):
        calls, load, pin, error = self.publish(paths=["books/example/section.tex"])
        self.assertIsNone(error)
        load.assert_not_called()
        pin.assert_not_called()
        self.assertFalse(any(call[0] == "docker" for call in calls))


class ImagePrCommitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.remote = self.root / "remote.git"
        self.work = self.root / "work"
        self.git("init", "--bare", str(self.remote), cwd=self.root)
        self.git("init", "-b", "main", str(self.work), cwd=self.root)
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        (self.work / "config").mkdir()
        (self.work / ".devcontainer").mkdir()
        (self.work / "config/container-image.txt").write_text("old\n")
        (self.work / ".devcontainer/devcontainer.json").write_text(
            '{"image": "old", "name": "preserve"}\n'
        )
        (self.work / "keep.txt").write_text("author content\n")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "origin", "HEAD:refs/heads/topic")
        self.head = self.git("rev-parse", "HEAD")
        self.pull = pull_request(self.head)
        self.dispatch_patch = patch.object(image_pr, "dispatch_validation")
        self.dispatch = self.dispatch_patch.start()
        self.addCleanup(self.dispatch_patch.stop)
        self.root_patch = patch.object(image_pr, "ROOT", self.work)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.work,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def test_commit_extends_original_head_and_changes_only_two_files(self):
        with patch.object(image_pr.github_artifacts, "api", return_value=self.pull):
            self.assertTrue(image_pr.append_pin("owner/repo", self.pull, IMAGE))
        self.git("fetch", "origin", "topic")
        tip = self.git("rev-parse", "FETCH_HEAD")
        self.assertEqual(self.git("rev-parse", f"{tip}^"), self.head)
        self.assertEqual(
            self.git("diff", "--name-only", self.head, tip).splitlines(),
            [".devcontainer/devcontainer.json", "config/container-image.txt"],
        )
        self.assertEqual(self.git("show", f"{tip}:config/container-image.txt"), IMAGE)
        self.assertEqual(
            json.loads(self.git("show", f"{tip}:.devcontainer/devcontainer.json")),
            {"image": IMAGE, "name": "preserve"},
        )
        self.assertEqual(self.git("status", "--short"), "")
        current = pull_request(tip)
        with patch.object(image_pr.github_artifacts, "api", return_value=current):
            self.assertFalse(image_pr.append_pin("owner/repo", current, IMAGE))
        self.assertEqual(
            self.git("ls-remote", "origin", "refs/heads/topic").split()[0], tip
        )

        self.dispatch.assert_called_once_with("owner/repo", "topic", tip)

    def test_stale_and_closed_prs_never_modify_branch(self):
        for current in ({**self.pull, "state": "closed"}, pull_request("new")):
            with patch.object(image_pr.github_artifacts, "api", return_value=current):
                self.assertFalse(image_pr.append_pin("owner/repo", self.pull, IMAGE))
        self.assertEqual(
            self.git("ls-remote", "origin", "refs/heads/topic").split()[0], self.head
        )

    def test_push_lease_preserves_concurrent_author_commit(self):
        (self.work / "keep.txt").write_text("new author content\n")
        self.git("commit", "-am", "author change")
        self.git("push", "origin", "HEAD:refs/heads/topic")
        new_head = self.git("rev-parse", "HEAD")
        with (
            patch.object(image_pr.github_artifacts, "api", return_value=self.pull),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            image_pr.append_pin("owner/repo", self.pull, IMAGE)
        self.assertEqual(
            self.git("ls-remote", "origin", "refs/heads/topic").split()[0], new_head
        )


class ImageDispatchTests(unittest.TestCase):
    def test_dispatch_uses_structured_exact_commit_input(self):
        with patch.object(image_pr, "command") as command:
            image_pr.dispatch_validation("owner/repo", "topic", "a" * 40)
        self.assertEqual(
            json.loads(command.call_args.kwargs["data"]),
            {"ref": "topic", "inputs": {"expected_sha": "a" * 40}},
        )
        self.assertIn(
            "repos/owner/repo/actions/workflows/build.yml/dispatches",
            command.call_args.args,
        )


if __name__ == "__main__":
    unittest.main()
