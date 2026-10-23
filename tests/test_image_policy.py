"""Runtime image policy output and complete declared-input identity."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_support import copy_validation_configuration

ROOT = Path(__file__).resolve().parent.parent


class ImagePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        copy_validation_configuration(self.root)
        (self.root / "scripts").mkdir(exist_ok=True)
        (self.root / "config").mkdir(exist_ok=True)
        for name in ("image_policy.py", "repository_config.py"):
            shutil.copyfile(ROOT / "scripts" / name, self.root / "scripts" / name)
        self.config = {
            "schema_version": 1,
            "policy_version": "native-multiarch-v1",
            "inputs": ["input.bin", "config/image-build.json"],
            "platforms": [
                {"arch": "amd64", "runner": "ubuntu-24.04"},
                {"arch": "arm64", "runner": "ubuntu-24.04-arm"},
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
                str(self.root / "scripts/image_policy.py"),
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

    def test_executable_modes_and_paths_change_identity_and_symlinks_fail(self) -> None:
        original = self.output("hash")
        source = self.root / "input.bin"
        source.chmod(0o755)
        executable = self.output("hash")
        self.assertNotEqual(executable, original)
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
        self.config["platforms"].append({"arch": "riscv64", "runner": "custom-runner"})
        self.config["policy_version"] = "native-multiarch-v2"
        self.save()
        self.assertEqual(
            json.loads(self.output("matrix")), {"include": self.config["platforms"]}
        )
        self.assertEqual(self.output("architectures"), "amd64 arm64 riscv64")
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
