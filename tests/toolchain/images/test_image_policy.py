"""Runtime image policy output and complete declared-input identity."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support.fixtures import copy_file, copy_validation_configuration

ROOT = Path(__file__).resolve().parents[3]


class ImagePolicyTests(unittest.TestCase):
    def test_published_tag_transcript_is_stable_across_deployed_readers(self) -> None:
        self.assertEqual(self.output("hash"), "7a9072be13e2")

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        copy_validation_configuration(self.root)
        (self.root / "scripts").mkdir(exist_ok=True)
        (self.root / "config").mkdir(exist_ok=True)
        for name in (
            "toolchain/images/image_policy.py",
            "repository/config/repository_config.py",
        ):
            copy_file(ROOT / "scripts" / name, self.root / "scripts" / name)
        self.config = {
            "schema_version": 1,
            "policy_version": "native-multiarch-v1",
            "inputs": ["input.bin", "config/image-build.json"],
            "platforms": [
                {"arch": "amd64", "runner": "ubuntu-26.04"},
                {"arch": "arm64", "runner": "ubuntu-26.04-arm"},
            ],
        }
        (self.root / "input.bin").write_bytes(b"binary\x00input\xff\n")
        self.save()

    def save(self) -> None:
        (self.root / "config/image-build.json").write_text(json.dumps(self.config))

    def command(self, consumer: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-S",
                str(self.root / "scripts/toolchain/images/image_policy.py"),
                consumer,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def output(self, consumer: str) -> str:
        result = self.command(consumer)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_checkout_modes_are_normalized_but_paths_and_symlinks_are_checked(
        self,
    ) -> None:
        original = self.output("hash")
        source = self.root / "input.bin"
        source.chmod(0o755)
        executable = self.output("hash")
        self.assertEqual(executable, original)
        source.chmod(0o644)
        self.assertEqual(self.output("hash"), original)
        target = self.root / "renamed.bin"
        source.rename(target)
        self.config["inputs"][0] = "renamed.bin"
        self.save()
        self.assertNotEqual(self.output("hash"), original)
        target.rename(source)
        target.symlink_to(source)
        result = self.command("hash")
        self.assertEqual(result.returncode, 1)
        self.assertIn("without symlinks", result.stderr)

    def test_runtime_matrix_and_architectures_follow_policy_without_generation(
        self,
    ) -> None:
        original = self.output("hash")
        self.config["platforms"].reverse()
        self.config["policy_version"] = "native-multiarch-v2"
        self.save()
        self.assertEqual(json.loads(self.output("matrix")), {"include": self.config["platforms"]})
        self.assertEqual(self.output("architectures"), "arm64 amd64")
        self.assertNotEqual(self.output("hash"), original)

    def test_only_declared_inputs_change_hash_and_missing_input_fails(self) -> None:
        original = self.output("hash")
        (self.root / "unrelated.txt").write_text("unrelated")
        self.assertEqual(self.output("hash"), original)
        (self.root / "input.bin").write_bytes(b"modified")
        self.assertNotEqual(self.output("hash"), original)
        (self.root / "input.bin").unlink()
        result = self.command("hash")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("error:", result.stderr)

    def test_invalid_configuration_never_emits_partial_outputs(self) -> None:
        self.config["platforms"] = [{"arch": "amd64", "runner": "invalid runner"}]
        self.save()
        for consumer in ("hash", "matrix", "architectures"):
            with self.subTest(consumer=consumer):
                result = self.command(consumer)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")

    def test_copy_permissions_and_unregistered_sources_fail_before_tagging(
        self,
    ) -> None:
        recipe = self.root / ".devcontainer/Dockerfile"
        recipe.parent.mkdir()
        recipe.write_text("FROM scratch\nCOPY input.bin /input\n")
        result = self.command("hash")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit --chmod", result.stderr)
        recipe.write_text("FROM scratch\nCOPY --chmod=0644 input.bin /input\n")
        result = self.command("hash")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unhashed Docker build inputs", result.stderr)
        self.config["inputs"] += [
            ".devcontainer/Dockerfile",
            ".devcontainer/Dockerfile.dockerignore",
        ]
        (recipe.parent / "Dockerfile.dockerignore").write_text("build/\n")
        self.save()
        self.assertEqual(self.command("hash").returncode, 0)
        recipe.write_text(recipe.read_text().replace("FROM scratch", "FROM debian:latest"))
        self.assertIn("immutable digest", self.command("hash").stderr)
        recipe.write_text(recipe.read_text().replace("FROM debian:latest", "FROM scratch"))
        recipe.write_text(recipe.read_text() + "COPY --from=other:latest /file /other\n")
        self.assertIn("immutable digest", self.command("hash").stderr)
        recipe.write_text("FROM scratch\nCOPY --chmod=0644 input.bin /input\n")
        recipe.write_text(recipe.read_text() + 'COPY --chmod=0644 ["unknown.bin", "/other"]\n')
        self.assertIn("unknown.bin", self.command("hash").stderr)
