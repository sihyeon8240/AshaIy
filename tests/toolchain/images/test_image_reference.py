"""Checks for canonical repository configuration and synchronized consumers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.repository.config import config_sync as SYNC
from scripts.repository.config import repository_config as CONFIG
from tests.support.fixtures import copy_file, copy_validation_configuration

ROOT = Path(__file__).resolve().parents[3]


class ConfigurationTests(unittest.TestCase):
    def test_issue_form_choices_preserve_other_content_and_escape_titles(self):
        from scripts.repository.source_reads import parse_yaml

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            title = 'Analysis \\ "Foundations" & Algebra'
            for path, text in SYNC.rendered_issue_forms(root, [{"title": title}]).items():
                original = path.read_text()
                form = parse_yaml(text)
                assert isinstance(form, dict)
                self.assertEqual(form["body"][0]["attributes"]["options"], [title])
                self.assertEqual(
                    re.sub(r"options: .*", "options: GENERATED", text),
                    re.sub(r"options: .*", "options: GENERATED", original),
                )

    def make_repository(self, root: Path) -> None:
        copy_validation_configuration(root)
        (root / ".vscode").mkdir(exist_ok=True)
        shutil.copy(ROOT / ".vscode/settings.json", root / ".vscode/settings.json")
        for relative in (
            "scripts",
            "config/schemas",
            ".github/actions/load-toolchain",
            "config/generated",
            ".devcontainer",
            ".github",
            ".github/workflows",
            ".github/ISSUE_TEMPLATE",
            "lean",
            "common/templates",
            ".vscode",
        ):
            (root / relative).mkdir(parents=True, exist_ok=True)
        for relative in (
            "config/ignore-patterns.yml",
            "config/image-build.json",
            "config/authoring.json",
            "config/validation-patterns.json",
            "config/schemas/books.schema.json",
            "config/schemas/chapters.schema.json",
            "config/schemas/sections.schema.json",
            "config/schemas/modules.schema.json",
            "config/schemas/image-build.schema.json",
            ".github/ISSUE_TEMPLATE/mathematical-error.yml",
            ".github/ISSUE_TEMPLATE/typo.yml",
            ".github/actions/load-toolchain/action.yml",
            ".github/workflows/build.yml",
            ".github/workflows/pages.yml",
            "scripts/site/pages_current.sh",
            "scripts/release/snapshot_base.sh",
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
        shutil.copytree(ROOT / ".devcontainer/generated", root / ".devcontainer/generated")
        shutil.copy(ROOT / "config/toolchain.env", root / "config/toolchain.env")
        shutil.copy(ROOT / "config/container-image.txt", root / "config/container-image.txt")
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

    def test_validation_changes_synchronize_runtime_schemas_and_standalone_shell(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            copy_file(
                ROOT / "scripts/repository/config/validation_patterns.py",
                root / "scripts/repository/config/validation_patterns.py",
            )
            path = root / "config/validation-patterns.json"
            data = json.loads(path.read_text())
            data["patterns"]["book_slug"] = "[a-z]+"
            data["patterns"]["git_commit"] = "[0-9a-f]{8}"
            data["patterns"]["sha256"] = "[0-9a-f]{8}"
            path.write_text(json.dumps(data))
            before = (root / "scripts/site/pages_current.sh").read_text()
            changed = SYNC.synchronize(root=root, check=True)
            self.assertIn(root / "config/schemas/books.schema.json", changed)
            self.assertIn(root / ".github/workflows/build-toolchain.yml", changed)
            self.assertIn(root / "scripts/site/pages_current.sh", changed)
            self.assertEqual((root / "scripts/site/pages_current.sh").read_text(), before)

            SYNC.synchronize(root=root)
            self.assertEqual(SYNC.synchronize(root=root, check=True), [])
            schema = json.loads((root / "config/schemas/books.schema.json").read_text())
            slug = schema["properties"]["books"]["items"]["properties"]["slug"]
            self.assertIsNotNone(re.search(slug["pattern"], "alpha"))
            self.assertIsNone(re.search(slug["pattern"], "alpha-beta"))
            script = (root / "scripts/site/pages_current.sh").read_text()
            operand = script.split("# validation-pattern: git_commit\n", 1)[1].splitlines()[0]
            for value, expected in (("a" * 8, 0), ("a" * 40, 1), ("g" * 8, 1)):
                result = subprocess.run(
                    ["bash", "-c", "SNAPSHOT_SHA=$1\n" + operand, "validation", value],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected, result.stderr)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from scripts.repository.config.validation_patterns import validation_pattern\n"
                    "\n"
                    "print(validation_pattern('image_digest'))\n",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(result.stdout.strip(), "sha256:[0-9a-f]{8}")
            self.assertEqual(script.replace("{8}", "{40}"), before)

    def test_invalid_shared_validation_never_writes_consumers(self):
        for updates in (
            {"sha256": "["},
            {"sha256": "${image_digest}"},
            {"sha256": "${missing}"},
            {"git_commit": "(?:[0-9a-f]){40}"},
        ):
            with (
                self.subTest(updates=updates),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                self.make_repository(root)
                path = root / "config/validation-patterns.json"
                data = json.loads(path.read_text())
                data["patterns"].update(updates)
                path.write_text(json.dumps(data))
                before = {file: file.read_bytes() for file in root.rglob("*") if file.is_file()}
                with self.assertRaises(ValueError):
                    SYNC.synchronize(root=root)
                self.assertEqual({file: file.read_bytes() for file in before}, before)

    def test_image_policy_changes_are_consumed_without_workflow_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_repository(root)
            path = root / "config/image-build.json"
            config = json.loads(path.read_text())
            config["inputs"].append("scripts/new-image-input.sh")
            config["policy_version"] = "native-multiarch-v2"
            config["platforms"].reverse()
            path.write_text(json.dumps(config))

            runtime_workflows = {
                root / f".github/workflows/{name}": (root / f".github/workflows/{name}").read_bytes()
                for name in ("prepare-image.yml", "build-toolchain.yml")
            }
            changed = SYNC.synchronize(root=root, check=True)
            self.assertNotIn(root / ".github/workflows/prepare-image.yml", changed)
            self.assertNotIn(root / ".github/workflows/build-toolchain.yml", changed)
            SYNC.synchronize(root=root)
            wrapper = (root / ".github/workflows/build-image.yml").read_text()
            self.assertNotIn("scripts/new-image-input.sh", wrapper)
            self.assertNotIn("push:", wrapper)
            for workflow, original in runtime_workflows.items():
                self.assertEqual(workflow.read_bytes(), original)
            self.assertEqual(SYNC.synchronize(root=root, check=True), [])

    def test_tool_versions_only_change_their_installation_group(self) -> None:
        toolchain = CONFIG.load_toolchain()
        original = SYNC.rendered_toolchain_groups(ROOT, toolchain)
        for key, group in (
            ("RUFF_VERSION", "tools"),
            ("PYYAML_VERSION", "python"),
            ("GH_VERSION", "tools"),
            ("TEXLIVE_ARCHIVE_DATE", "texlive"),
            ("LEAN_TOOLCHAIN", "lean"),
        ):
            with self.subTest(key=key):
                changed = SYNC.rendered_toolchain_groups(ROOT, {**toolchain, key: "changed"})
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
                    (root / "config/image-build.json").write_text(json.dumps({**config, "inputs": inputs}))
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
            path.write_text(text.replace("- '*.pyc'", "- '$(error injected)'"), encoding="utf-8")
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
            (root / "lean/lean-toolchain").write_text("leanprover/lean4:v0.0.0\n", encoding="utf-8")
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
            devcontainer = json.loads((root / ".devcontainer/devcontainer.json").read_text(encoding="utf-8"))
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
                toolchain.read_text().replace(CONFIG.load_toolchain()["LEAN_VERSION"], "99.0.0"),
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
            from scripts.repository import file_updates

            replace = file_updates.os.replace

            def fail_consumer(source, destination):
                if destination == consumer:
                    raise OSError("simulated write failure")
                return replace(source, destination)

            with (
                patch.object(file_updates.os, "replace", fail_consumer),
                self.assertRaisesRegex(OSError, "simulated write failure"),
            ):
                SYNC.set_image_digest("b" * 64, root=root)
            self.assertEqual({path: path.read_bytes() for path in originals}, originals)


if __name__ == "__main__":
    unittest.main()
