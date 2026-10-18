"""Schema validation covers nested manifests without reading ignored inputs."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from check_quality import check_schemas

ROOT = Path(__file__).resolve().parent.parent


class SchemaQualityTests(unittest.TestCase):
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
