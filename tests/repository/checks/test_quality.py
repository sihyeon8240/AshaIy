"""Schema validation covers nested manifests without reading ignored inputs."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.repository.checks import check_quality as QUALITY
from scripts.repository.checks.check_quality import check_schemas
from tests.support.fixtures import copy_file

ROOT = Path(__file__).resolve().parents[3]


class SchemaQualityTests(unittest.TestCase):
    def test_type_gate_checks_both_source_trees_and_rejects_cross_module_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("scripts", "tests", "config", ".vscode"):
                (root / directory).mkdir()
            copy_file(ROOT / "config/pyproject.toml", root / "config/pyproject.toml")
            (root / ".vscode/settings.json").write_text('{"yaml.schemas": {}}\n')
            (root / "scripts/__init__.py").touch()
            (root / "tests/__init__.py").touch()
            source = root / "scripts/example.py"
            source.write_text("def number(value: int) -> int:\n    return value\n")
            test = root / "tests/example.py"
            test.write_text("from scripts.example import number\nvalue = number(1)\n")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            with patch.object(QUALITY, "ROOT", root):
                self.assertEqual(QUALITY.main(), 0)
                source.write_text("def number(value: int) -> int:\n    return 'invalid return'\n")
                test.write_text("from scripts.example import number\nvalue = number('invalid argument')\n")
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    self.assertNotEqual(QUALITY.main(), 0)
                diagnostics = output.getvalue()
                self.assertIn("invalid-return-type", diagnostics)
                self.assertIn("invalid-argument-type", diagnostics)
                self.assertIn("scripts/example.py", diagnostics)
                self.assertIn("tests/example.py", diagnostics)

    def test_json_editor_associations_also_validate_cli_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".vscode").mkdir()
            (root / "config/schemas").mkdir(parents=True)
            schema = Path("config/schemas/authoring.schema.json")
            copy_file(ROOT / schema, root / schema)
            (root / ".vscode/settings.json").write_text(
                json.dumps(
                    {
                        "yaml.schemas": {},
                        "json.schemas": [
                            {
                                "url": str(schema),
                                "fileMatch": ["/config/authoring.json"],
                            }
                        ],
                    }
                )
            )
            path = Path("config/authoring.json")
            data = json.loads((ROOT / path).read_text())
            (root / path).write_text(json.dumps({**data, "unexpected": True}))
            self.assertNotEqual(check_schemas(root, {path, schema}), 0)
            (root / path).write_text(json.dumps(data))
            self.assertEqual(check_schemas(root, {path, schema}), 0)

    def setUp(self) -> None:
        original_run = subprocess.run

        def buffered_run(*arguments, **options):
            if any(name in options for name in ("stdout", "stderr", "capture_output")):
                return original_run(*arguments, **options)
            result = original_run(*arguments, **options, capture_output=True, text=True)
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            return result

        # Forward child output to unittest's buffer so failures retain diagnostics.
        self.enterContext(
            patch(
                "scripts.repository.checks.check_quality.subprocess.run",
                side_effect=buffered_run,
            )
        )

    def test_nested_manifest_rejects_reserved_module_and_excludes_unselected_files(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".vscode").mkdir()
            (root / ".vscode/settings.json").write_text(
                json.dumps({"yaml.schemas": {"config/schemas/modules.schema.json": ["/lean/Textbooks/**/modules.yml"]}})
            )
            schema = Path("config/schemas/modules.schema.json")
            (root / schema).parent.mkdir(parents=True)
            copy_file(ROOT / schema, root / schema)
            manifest = Path("lean/Textbooks/Sample/Appendices/Topic/modules.yml")
            (root / manifest).parent.mkdir(parents=True)
            (root / manifest).write_text("schema_version: 1\nmodules: [All]\n")
            self.assertNotEqual(check_schemas(root, {schema, manifest}), 0)
            self.assertEqual(check_schemas(root, {schema}), 0)
            (root / manifest).write_text("schema_version: 1\nmodules: [Foundations]\n")
            self.assertEqual(check_schemas(root, {schema, manifest}), 0)

    def test_invalid_schema_is_rejected_without_matching_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".vscode").mkdir()
            (root / ".vscode/settings.json").write_text('{"yaml.schemas": {}}\n')
            schema = Path("config/schemas/invalid.schema.json")
            (root / schema).parent.mkdir(parents=True)
            (root / schema).write_text('{"type": "invalid"}\n')
            self.assertNotEqual(check_schemas(root, {schema}), 0)


if __name__ == "__main__":
    unittest.main()
