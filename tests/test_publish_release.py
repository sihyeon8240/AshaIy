"""Publication integration tests using a local Git remote and a fake GitHub API."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_support import git_environment, write_executable

ROOT = Path(__file__).resolve().parent.parent


class PublishReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.environment = git_environment()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        scripts = self.repo / "scripts"
        scripts.mkdir()
        for name in ["publish-release.sh", "upload-release-assets.sh"]:
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        (scripts / "books.py").write_text('print("1.1.0")\n')
        validator = scripts / "release-plan.sh"
        write_executable(validator, "#!/usr/bin/env bash\nexit 0\n")
        self.git("add", ".")
        self.git("commit", "-m", "Initial")
        self.sha = self.git("rev-parse", "HEAD")
        origin = self.root / "origin.git"
        subprocess.run(
            ["git", "init", "--bare", str(origin)],
            env=self.environment,
            check=True,
            capture_output=True,
            timeout=10,
        )
        self.git("remote", "add", "origin", str(origin))
        self.git("push", "origin", "main")
        self.package = self.repo / "build" / "release"
        self.package.mkdir(parents=True)
        self.tag = "alpha-v1.1.0"
        self.pdf = self.package / f"{self.tag}.pdf"
        self.pdf.write_bytes(b"%PDF-test")
        self.checksum = self.package / "SHA256SUMS"
        self.checksum.write_text(
            f"{hashlib.sha256(self.pdf.read_bytes()).hexdigest()}  {self.pdf.name}\n"
        )
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.state = self.root / "state.json"
        self.state.write_text(json.dumps({"draft": None, "assets": {}, "calls": []}))
        gh = self.bin / "gh"
        write_executable(
            gh,
            """#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
path = pathlib.Path(os.environ["FAKE_GH_STATE"])
s = json.loads(path.read_text())
a = sys.argv[1:]
s["calls"].append(a)
path.write_text(json.dumps(s))
if os.environ.get("FAIL_GH") == " ".join(a[:2]):
    sys.exit(1)
if a[0] == "api":
    if s["draft"] is not None:
        print(str(s["draft"]).lower())
elif a[:2] == ["release", "create"]:
    if "--verify-tag" in a:
        subprocess.run(
            ["git", "ls-remote", "--exit-code", "--tags", "origin", "refs/tags/" + a[2]],
            check=True,
            capture_output=True,
        )
    s["draft"] = True
elif a[:2] == ["release", "view"]:
    print("\\n".join(s["assets"]))
elif a[:2] == ["release", "upload"]:
    for name in a[3:]:
        p = pathlib.Path(name)
        s["assets"][p.name] = p.read_bytes().hex()
elif a[:2] == ["release", "download"]:
    dest = pathlib.Path(a[a.index("--dir") + 1])
    for i, arg in enumerate(a):
        if arg == "--pattern":
            name = a[i + 1]
            (dest / name).write_bytes(bytes.fromhex(s["assets"][name]))
elif a[:2] == ["release", "edit"]:
    assert "--draft=false" in a
    s["draft"] = False
else:
    sys.exit(98)
path.write_text(json.dumps(s))
""",
        )

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args],
            cwd=self.repo,
            env=self.environment,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).strip()

    def run_publish(self, **env):
        return subprocess.run(
            [str(self.repo / "scripts/publish-release.sh"), "alpha", str(self.package)],
            cwd=self.repo,
            env={
                **self.environment,
                "PATH": f"{self.bin}:{os.environ['PATH']}",
                "GITHUB_ACTIONS": "true",
                "GITHUB_EVENT_NAME": "push",
                "GITHUB_REF": "refs/heads/main",
                "GITHUB_SHA": self.sha,
                "GITHUB_REPOSITORY": "owner/test",
                "FAKE_GH_STATE": str(self.state),
                **env,
            },
            text=True,
            capture_output=True,
            timeout=10,
        )

    def test_success_publishes_verified_assets_and_retry_is_noop(self):
        result = self.run_publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(self.state.read_text())
        self.assertFalse(state["draft"])
        self.assertEqual(set(state["assets"]), {self.pdf.name, "SHA256SUMS"})
        self.assertEqual(self.git("cat-file", "-t", f"refs/tags/{self.tag}"), "tag")
        self.assertEqual(self.git("rev-list", "-n", "1", self.tag), self.sha)
        count = len(state["calls"])
        result = self.run_publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = json.loads(self.state.read_text())["calls"][count:]
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "api")
        self.assertEqual(calls[1][:2], ["release", "download"])

    def test_public_assets_missing_or_changed_fail_without_writes(self):
        result = self.run_publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        original = json.loads(self.state.read_text())
        for name in (self.pdf.name, "SHA256SUMS"):
            for missing in (True, False):
                with self.subTest(name=name, missing=missing):
                    state = json.loads(json.dumps(original))
                    state["calls"] = []
                    if missing:
                        del state["assets"][name]
                    else:
                        state["assets"][name] = b"changed".hex()
                    self.state.write_text(json.dumps(state))
                    result = self.run_publish()
                    self.assertNotEqual(result.returncode, 0)
                    after = json.loads(self.state.read_text())
                    self.assertFalse(after["draft"])
                    self.assertEqual(after["assets"], state["assets"])
                    self.assertTrue(
                        all(
                            call[:2]
                            not in [
                                ["release", "upload"],
                                ["release", "edit"],
                                ["release", "create"],
                            ]
                            for call in after["calls"]
                        )
                    )

    def test_interrupted_upload_resumes_original_package(self):
        failed = self.run_publish(FAIL_GH="release upload")
        self.assertNotEqual(failed.returncode, 0)
        self.assertTrue(json.loads(self.state.read_text())["draft"])
        resumed = self.run_publish()
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertFalse(json.loads(self.state.read_text())["draft"])

    def test_rejected_tag_push_retries_same_local_tag_before_publication(self):
        hook = self.root / "origin.git" / "hooks" / "pre-receive"
        write_executable(hook, "#!/usr/bin/env bash\nexit 1\n")

        for attempt in range(2):
            with self.subTest(attempt=attempt):
                failed = self.run_publish()
                self.assertNotEqual(failed.returncode, 0)
                self.assertEqual(json.loads(self.state.read_text())["calls"], [])
                self.assertEqual(
                    self.git("ls-remote", "--tags", "origin", f"refs/tags/{self.tag}"),
                    "",
                )

        local_tag = self.git("rev-parse", f"refs/tags/{self.tag}")
        hook.unlink()
        resumed = self.run_publish()
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(
            self.git("ls-remote", "--tags", "origin", f"refs/tags/{self.tag}"),
            f"{local_tag}\trefs/tags/{self.tag}",
        )
        self.assertFalse(json.loads(self.state.read_text())["draft"])

    def test_conflicting_annotated_remote_tag_is_preserved(self):
        self.git("commit", "--allow-empty", "-m", "Different source")
        different_source = self.git("rev-parse", "HEAD")
        self.git("tag", "-a", self.tag, "-m", "Conflicting release")
        self.git("push", "origin", f"refs/tags/{self.tag}")
        self.git("checkout", "--detach", self.sha)

        result = self.run_publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.state.read_text())["calls"], [])
        self.assertEqual(
            self.git("ls-remote", "--tags", "origin", f"refs/tags/{self.tag}^{{}}"),
            f"{different_source}\trefs/tags/{self.tag}^{{}}",
        )

    def test_original_package_retry_after_main_advances(self):
        failed = self.run_publish(FAIL_GH="release upload")
        self.assertNotEqual(failed.returncode, 0)
        state = json.loads(self.state.read_text())
        state["assets"][self.pdf.name] = self.pdf.read_bytes().hex()
        self.state.write_text(json.dumps(state))
        (self.repo / "later-content").write_text("newer main content")
        self.git("add", "later-content")
        self.git("commit", "-m", "Later main")
        self.git("push", "origin", "main")
        newer = self.git("rev-parse", "HEAD")
        self.git("checkout", "--detach", self.sha)
        result = self.run_publish(
            GITHUB_EVENT_NAME="workflow_dispatch",
            GITHUB_SHA=newer,
            RELEASE_SOURCE_SHA=self.sha,
            RELEASE_RETRY_VALIDATED=self.sha,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("rev-list", "-n", "1", self.tag), self.sha)
        state = json.loads(self.state.read_text())
        self.assertFalse(state["draft"])
        uploads = [call for call in state["calls"] if call[:2] == ["release", "upload"]]
        self.assertEqual(uploads[-1][3:], [str(self.checksum)])

    def test_unvalidated_manual_retry_cannot_publish(self):
        result = self.run_publish(GITHUB_EVENT_NAME="workflow_dispatch")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.state.read_text())["calls"], [])

    def test_conflicting_asset_is_not_overwritten_or_published(self):
        self.state.write_text(
            json.dumps(
                {
                    "draft": True,
                    "assets": {self.pdf.name: b"different".hex()},
                    "calls": [],
                }
            )
        )
        result = self.run_publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("different content", result.stderr)
        state = json.loads(self.state.read_text())
        self.assertTrue(state["draft"])
        self.assertFalse(
            any(
                c[:2] in [["release", "edit"], ["release", "upload"]]
                for c in state["calls"]
            )
        )

    def test_non_main_and_wrong_checkout_fail_before_remote_writes(self):
        for env in [
            {"GITHUB_REF": "refs/heads/local-work"},
            {"GITHUB_EVENT_NAME": "pull_request"},
            {"GITHUB_SHA": "0" * 40},
        ]:
            result = self.run_publish(**env)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(self.state.read_text())["calls"], [])
            self.assertEqual(self.git("tag", "--list"), "")

    def test_conflicting_tag_fails(self):
        self.git("tag", self.tag)
        self.git("push", "origin", self.tag)
        result = self.run_publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not annotated", result.stderr)
        self.assertEqual(json.loads(self.state.read_text())["calls"], [])

    def test_tampered_package_fails_before_tagging(self):
        self.pdf.write_bytes(b"changed")
        result = self.run_publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("tag", "--list"), "")

    def test_advanced_main_still_tags_validated_commit(self):
        self.git("commit", "--allow-empty", "-m", "Later main")
        self.git("push", "origin", "main")
        self.git("checkout", "--detach", self.sha)
        result = self.run_publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("rev-list", "-n", "1", self.tag), self.sha)

    def test_failed_verification_keeps_draft(self):
        result = self.run_publish(FAIL_GH="release download")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(json.loads(self.state.read_text())["draft"])


if __name__ == "__main__":
    unittest.main()
