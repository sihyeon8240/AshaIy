"""Theorem ownership, policy overrides, counter references, and stale output."""

from __future__ import annotations

import copy
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import yaml

from scripts.latex.theorem_generation import GENERATED, MANIFEST, checked_manifest, generate
from scripts.latex.theorem_manifest import load_theorems
from tests.support.fixtures import write_yaml

ROOT = Path(__file__).resolve().parents[2]


class TheoremManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / MANIFEST
        self.document = yaml.safe_load((ROOT / MANIFEST).read_text())
        self.write_manifest()

    def write_manifest(self) -> None:
        write_yaml(self.path, self.document)

    def generate(self, *, check: bool = False) -> int:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return generate(root=self.root, check=check)

    def test_check_is_read_only_and_generation_is_idempotent(self) -> None:
        self.assertEqual(self.generate(check=True), 1)
        self.assertFalse((self.root / GENERATED).exists())
        self.assertFalse((self.root / "build").exists())
        self.assertEqual(self.generate(), 0)
        output = self.root / GENERATED
        original = output.read_bytes(), output.stat().st_mtime_ns
        self.assertEqual(self.generate(), 0)
        self.assertEqual(self.generate(check=True), 0)
        self.assertEqual((output.read_bytes(), output.stat().st_mtime_ns), original)
        self.document["environments"]["theorem"]["title"] = "Changed theorem"
        self.write_manifest()
        self.assertEqual(self.generate(check=True), 1)
        self.assertEqual((output.read_bytes(), output.stat().st_mtime_ns), original)
        with self.assertRaisesRegex(ValueError, "ashaiy theorems generate"):
            checked_manifest(self.root)
        self.generate()
        self.assertIn("Changed theorem", output.read_text())

    def test_add_remove_and_override_policies_independently(self) -> None:
        self.document["environments"]["claim"] = {
            "kind": "theorem",
            "title": "Claim",
            "style": "plain",
            "counter": {"shared": "theorem"},
            "space_after": "none",
        }
        self.document["environments"]["remark"]["break_before_initial_list"] = False
        self.write_manifest()
        self.generate()
        manifest = checked_manifest(self.root)
        self.assertIn("claim", manifest.numbered_environments)
        self.assertNotIn("remark", manifest.numbered_environments)
        output = (self.root / GENERATED).read_text()
        self.assertIn(r"\newtheorem{claim}[theorem]{Claim}", output)
        self.assertIn("textbook@listhead@claim", output)
        self.assertNotIn("env/claim/after", output)
        self.assertIn(r"\AddToHook{env/remark/after}{\par\bigskip}", output)
        self.assertNotIn("textbook@listhead@remark", output)
        self.assertNotIn(r"\newtheorem{proof}", output)
        self.assertNotIn(r"\newtheorem*{proof}", output)
        self.assertIn(r"\Crefname{definition}{Definition}{Definitions}", output)
        del self.document["environments"]["claim"]
        self.document["list_environments"] = []
        self.write_manifest()
        self.generate()
        output = (self.root / GENERATED).read_text()
        self.assertNotIn("claim", output)
        self.assertNotIn("breakbeforelist", output)

    def test_invalid_manifests_preserve_generated_output(self) -> None:
        self.generate()
        original = (self.root / GENERATED).read_bytes()
        valid = copy.deepcopy(self.document)
        invalid = []
        for field, value in (
            ("schema_version", True),
            ("schema_version", 2),
            ("unknown", True),
            ("defaults", {}),
            ("list_environments", ["enumerate", "enumerate"]),
            ("list_environments", ["equation"]),
            ("list_environments", [[]]),
            ("environments", {}),
            ("environments", {1: {}}),
        ):
            invalid.append(valid | {field: value})
        for changes in (
            {"title": "{"},
            {"title": "#1"},
            {"title": "Title% comment"},
            {"title": "two\nlines"},
            {"style": "unsupported"},
            {"kind": "raw"},
            {"space_after": "large"},
            {"break_before_initial_list": 1},
            {"counter": {"within": "unknown"}},
            {"counter": {"shared": "missing"}},
            {"counter": {"shared": "theorem"}},
            {"counter": {"shared": "remark"}},
            {"counter": {"within": "section", "shared": "theorem"}},
            {"cref": {"singular": "theorem"}},
        ):
            data = copy.deepcopy(valid)
            data["environments"]["theorem"].update(changes)
            invalid.append(data)
        for name, declaration in (
            ("proof", {"kind": "theorem", "title": "Proof", "style": "plain", "counter": None}),
            ("proof", {"kind": "provided", "provider": "unknown"}),
            ("other", {"kind": "provided", "provider": "amsthm"}),
            ("enumerate", valid["environments"]["theorem"]),
            ("bad/name", valid["environments"]["theorem"]),
        ):
            data = copy.deepcopy(valid)
            data["environments"][name] = declaration
            invalid.append(data)
        for document in invalid:
            with self.subTest(document=document):
                write_yaml(self.path, document)
                with self.assertRaises(ValueError):
                    self.generate()
                self.assertEqual((self.root / GENERATED).read_bytes(), original)

    def test_yaml_duplicates_and_merges_report_source_locations(self) -> None:
        source = self.path.read_text()
        self.path.write_text(source + "schema_version: 1\n")
        with self.assertRaisesRegex(ValueError, r"theorems.yml:\d+:\d+:.*"):
            load_theorems(self.path)
        self.path.write_text("schema_version: 1\ndefaults: {<<: {space_after: bigskip}}\n")
        with self.assertRaisesRegex(ValueError, "merge keys are unsupported"):
            load_theorems(self.path)


if __name__ == "__main__":
    unittest.main()
