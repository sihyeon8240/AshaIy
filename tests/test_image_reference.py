"""Checks for canonical repository configuration and synchronized consumers."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

CONFIG_SPEC = importlib.util.spec_from_file_location(
    "repository_config", ROOT / "scripts/repository_config.py"
)
assert CONFIG_SPEC and CONFIG_SPEC.loader
CONFIG = importlib.util.module_from_spec(CONFIG_SPEC)
CONFIG_SPEC.loader.exec_module(CONFIG)

SYNC_SPEC = importlib.util.spec_from_file_location(
    "config_sync", ROOT / "scripts/config_sync.py"
)
assert SYNC_SPEC and SYNC_SPEC.loader
SYNC = importlib.util.module_from_spec(SYNC_SPEC)
SYNC_SPEC.loader.exec_module(SYNC)


class ConfigurationTests(unittest.TestCase):
    def make_repository(self, root: Path) -> None:
        (root / ".vscode").mkdir(exist_ok=True)
        shutil.copy(ROOT / ".vscode/settings.json", root / ".vscode/settings.json")
        for relative in (
            "config/generated",
            ".devcontainer",
            ".github",
            ".github/workflows",
            "lean",
            "common/templates",
            ".vscode",
        ):
            (root / relative).mkdir(parents=True, exist_ok=True)
        for relative in (
            "config/ignore-patterns.yml",
            "config/image-build.json",
            "config/authoring.json",
            ".github/workflows/prepare-image.yml",
            ".github/workflows/build-image.yml",
            ".github/workflows/build-toolchain.yml",
            "config/generated/cleanup-files.txt",
            "config/generated/cleanup-prune.txt",
            ".gitignore",
            ".devcontainer/Dockerfile.dockerignore",
            ".vscode/extensions.json",
            ".vscode/tasks.json",
            "config/books.yml",
        ):
            shutil.copy(ROOT / relative, root / relative)
        shutil.copytree(
            ROOT / ".devcontainer/generated", root / ".devcontainer/generated"
        )
        shutil.copy(ROOT / "config/toolchain.env", root / "config/toolchain.env")
        shutil.copy(
            ROOT / "config/container-image.txt", root / "config/container-image.txt"
        )
        shutil.copy(
            ROOT / ".devcontainer/devcontainer.json",
            root / ".devcontainer/devcontainer.json",
        )
        shutil.copy(
            ROOT / ".github/requirements-ci.txt",
            root / ".github/requirements-ci.txt",
        )
        shutil.copy(ROOT / "lean/lean-toolchain", root / "lean/lean-toolchain")
        shutil.copy(ROOT / "lean/lakefile.toml", root / "lean/lakefile.toml")
        shutil.copy(ROOT / "config/pyproject.toml", root / "config/pyproject.toml")
        shutil.copy(ROOT / "lean/lake-manifest.json", root / "lean/lake-manifest.json")
        shutil.copy(
            ROOT / "common/templates/formalization-versions.tex",
            root / "common/templates/formalization-versions.tex",
        )

    def test_image_policy_changes_only_regenerate_static_trigger_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            path = root / "config/image-build.json"
            config = json.loads(path.read_text())
            config["inputs"].append("scripts/new-image-input.sh")
            config["policy_version"] = "native-multiarch-v2"
            config["platforms"].append({"arch": "riscv64", "runner": "custom-runner"})
            path.write_text(json.dumps(config))

            runtime_workflows = {
                root / f".github/workflows/{name}": (
                    root / f".github/workflows/{name}"
                ).read_bytes()
                for name in ("prepare-image.yml", "build-toolchain.yml")
            }
            changed = SYNC.synchronize(root=root, check=True)
            self.assertNotIn(root / ".github/workflows/prepare-image.yml", changed)
            self.assertNotIn(root / ".github/workflows/build-toolchain.yml", changed)
            SYNC.synchronize(root=root)
            wrapper = (root / ".github/workflows/build-image.yml").read_text()
            self.assertIn("scripts/new-image-input.sh", wrapper)
            for workflow, original in runtime_workflows.items():
                self.assertEqual(workflow.read_bytes(), original)
            self.assertEqual(SYNC.synchronize(root=root, check=True), [])

    def test_tool_versions_only_change_their_installation_group(self) -> None:
        toolchain = CONFIG.load_toolchain()
        original = SYNC.rendered_toolchain_groups(ROOT, toolchain)
        for key, group in (
            ("RUFF_VERSION", "tools"),
            ("PYYAML_VERSION", "python"),
            ("GH_VERSION", "system"),
            ("TEXLIVE_ARCHIVE_DATE", "texlive"),
            ("LEAN_TOOLCHAIN", "lean"),
        ):
            with self.subTest(key=key):
                changed = SYNC.rendered_toolchain_groups(
                    ROOT, {**toolchain, key: "changed"}
                )
                self.assertEqual(
                    [path for path in original if original[path] != changed[path]],
                    [ROOT / ".devcontainer/generated" / f"{group}.env"],
                )

    def test_invalid_image_policy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            config = CONFIG.load_image_build()
            for inputs in (
                ["../outside"],
                ["config/image-build.json", "config/image-build.json"],
            ):
                with self.subTest(inputs=inputs):
                    (root / "config/image-build.json").write_text(
                        json.dumps({**config, "inputs": inputs})
                    )
                    with self.assertRaises(ValueError):
                        CONFIG.load_image_build(root)

    def test_invalid_mutable_image_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "image.txt"
            path.write_text("ghcr.io/example/latex:latest\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "immutable GHCR"):
                CONFIG.load_image(path)

    def test_ignore_profile_changes_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            path = root / "config/ignore-patterns.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("- '*.pyc'", "- '*.pyo'"), encoding="utf-8")
            expected = [
                root / ".gitignore",
                root / ".devcontainer/Dockerfile.dockerignore",
            ]
            self.assertEqual(SYNC.synchronize(root=root, check=True), expected)
            self.assertEqual(SYNC.synchronize(root=root), expected)
            self.assertEqual(SYNC.synchronize(root=root, check=True), [])

    def test_ignore_patterns_reject_shell_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            path = root / "config/ignore-patterns.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("- '*.pyc'", "- '$(error injected)'"), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "invalid pattern"):
                SYNC.synchronize(root=root)

    def test_toolchain_relationships_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "toolchain.env"
            text = (ROOT / "config/toolchain.env").read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    f"LEAN_TOOLCHAIN={CONFIG.load_toolchain()['LEAN_TOOLCHAIN']}",
                    "LEAN_TOOLCHAIN=leanprover/lean4:v0.0.0",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "LEAN_TOOLCHAIN must be"):
                CONFIG.load_toolchain(path)

    def test_drift_is_reported_and_synchronized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            (root / "lean/lean-toolchain").write_text(
                "leanprover/lean4:v0.0.0\n", encoding="utf-8"
            )
            self.assertEqual(
                SYNC.synchronize(root=root, check=True),
                [root / "lean/lean-toolchain"],
            )
            self.assertEqual(
                SYNC.synchronize(root=root),
                [root / "lean/lean-toolchain"],
            )
            self.assertEqual(SYNC.synchronize(root=root, check=True), [])

    def test_image_update_changes_only_canonical_and_derived_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            changed = SYNC.set_image_digest("b" * 64, root=root)
            expected = f"ghcr.io/sihyeon8240/ashaiy@sha256:{'b' * 64}"
            self.assertEqual(
                (root / "config/container-image.txt").read_text(encoding="utf-8"),
                expected + "\n",
            )
            devcontainer = json.loads(
                (root / ".devcontainer/devcontainer.json").read_text(encoding="utf-8")
            )
            self.assertEqual(devcontainer["image"], expected)
            self.assertEqual(
                changed,
                [
                    root / "config/container-image.txt",
                    root / ".devcontainer/devcontainer.json",
                ],
            )

    def test_publication_versions_follow_toolchain_and_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            toolchain = root / "config/toolchain.env"
            toolchain.write_text(
                toolchain.read_text().replace(
                    CONFIG.load_toolchain()["LEAN_VERSION"], "99.0.0"
                ),
                encoding="utf-8",
            )
            lock = root / "lean/lake-manifest.json"
            manifest = json.loads(lock.read_text())
            mathlib = next(p for p in manifest["packages"] if p["name"] == "mathlib")
            mathlib.update(inputRev="v99.0.0", rev="a" * 40)
            lock.write_text(json.dumps(manifest), encoding="utf-8")
            versions = root / "common/templates/formalization-versions.tex"
            before = versions.read_text()
            self.assertIn(versions, SYNC.synchronize(root=root, check=True))
            self.assertEqual(versions.read_text(), before)
            SYNC.synchronize(root=root)
            rendered = versions.read_text()
            self.assertIn(r"\TextbookLeanVersion}{99.0.0}", rendered)
            self.assertIn(r"\TextbookMathlibVersion}{v99.0.0}", rendered)
            self.assertIn(r"\TextbookMathlibRevision}{" + "a" * 40 + "}", rendered)
            self.assertEqual(SYNC.synchronize(root=root, check=True), [])
            versions.unlink()
            self.assertIn(versions, SYNC.synchronize(root=root, check=True))
            SYNC.synchronize(root=root)
            self.assertEqual(versions.read_text(), rendered)

    def test_invalid_mathlib_lock_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            lock = root / "lean/lake-manifest.json"
            manifest = json.loads(lock.read_text())
            mathlib = next(p for p in manifest["packages"] if p["name"] == "mathlib")
            mathlib["rev"] = "not-a-commit"
            lock.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "full Mathlib commit hash"):
                SYNC.synchronize(root=root)

    def test_image_update_rejects_non_sha256_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            with self.assertRaisesRegex(ValueError, "exactly 64 lowercase"):
                SYNC.set_image_digest("a" * 40, root=root)

    def test_image_update_validates_all_consumers_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            paths = (
                root / "config/container-image.txt",
                root / ".devcontainer/devcontainer.json",
            )
            originals = {path: path.read_bytes() for path in paths}
            (root / "lean/lake-manifest.json").write_text('{"packages": []}')
            with self.assertRaisesRegex(ValueError, "exactly one Mathlib"):
                SYNC.set_image_digest("b" * 64, root=root)
            self.assertEqual({path: path.read_bytes() for path in paths}, originals)

    def test_image_update_restores_originals_after_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            image = root / "config/container-image.txt"
            consumer = root / ".devcontainer/devcontainer.json"
            originals = {path: path.read_bytes() for path in (image, consumer)}
            write_text = Path.write_text

            def fail_consumer(path, *args, **kwargs):
                if path == consumer:
                    raise OSError("simulated write failure")
                return write_text(path, *args, **kwargs)

            with patch.object(Path, "write_text", fail_consumer):
                with self.assertRaisesRegex(OSError, "simulated write failure"):
                    SYNC.set_image_digest("b" * 64, root=root)
            self.assertEqual({path: path.read_bytes() for path in originals}, originals)


if __name__ == "__main__":
    unittest.main()
