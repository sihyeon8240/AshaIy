"""Schema validation covers nested manifests without reading ignored inputs."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_quality import check_schemas

ROOT = Path(__file__).resolve().parent.parent


class SchemaQualityTests(unittest.TestCase):
    def test_json_editor_associations_also_validate_cli_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".vscode").mkdir()
            (root / "config/schemas").mkdir(parents=True)
            schema = Path("config/schemas/authoring.schema.json")
            shutil.copy2(ROOT / schema, root / schema)
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
            result = original_run(*arguments, **options, capture_output=True, text=True)
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            return result

        # Forward child output to unittest's buffer so failures retain diagnostics.
        self.enterContext(
            patch("scripts.check_quality.subprocess.run", side_effect=buffered_run)
        )

    def test_nested_manifest_rejects_reserved_module_and_excludes_unselected_files(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".vscode").mkdir()
            (root / ".vscode/settings.json").write_text(
                json.dumps(
                    {
                        "yaml.schemas": {
                            "config/schemas/modules.schema.json": [
                                "/lean/Textbooks/**/modules.yml"
                            ]
                        }
                    }
                )
            )
            schema = Path("config/schemas/modules.schema.json")
            (root / schema).parent.mkdir(parents=True)
            shutil.copy2(ROOT / schema, root / schema)
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
