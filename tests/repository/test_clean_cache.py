"""Tests for selective local-cache cleanup."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.repository import python_cache
from tests.support.fixtures import copy_file, write_executable

ROOT = Path(__file__).resolve().parents[2]


class CleanCacheTests(unittest.TestCase):
    def test_stale_pruning_preserves_live_paths_other_caches_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "temporary"
            source.mkdir()
            (source / "live").mkdir()
            cache = root / ".cache/python" / source.relative_to(source.anchor)
            stale = cache / "gone/module.pyc"
            live = cache / "live/module.pyc"
            shared = root / ".cache/python/usr/shared.pyc"
            for path in (stale, live, shared):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"bytecode")
            (cache / "external").symlink_to(shared.parent, target_is_directory=True)
            with patch.object(python_cache.tempfile, "gettempdir", return_value=str(source)):
                python_cache.prune(root=root, dry_run=True)
                self.assertTrue(stale.exists())
                python_cache.prune(root=root)
            self.assertFalse(stale.exists())
            self.assertEqual(live.read_bytes(), b"bytecode")
            self.assertEqual(shared.read_bytes(), b"bytecode")
            self.assertTrue((cache / "external").is_symlink())

    def test_stale_pruning_rejects_symlinked_cache_parents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            external = Path(temporary) / "external"
            external.mkdir()
            sentinel = external / "keep"
            sentinel.write_text("preserved")
            (root / ".cache").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "refusing symlinked cache path"):
                python_cache.prune(root=root)
            self.assertEqual(sentinel.read_text(), "preserved")

    def test_temporary_workspace_cleans_its_bytecode_even_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prefix = Path(temporary) / "bytecode"
            shared = prefix / "usr/shared.pyc"
            shared.parent.mkdir(parents=True)
            shared.write_bytes(b"shared")
            with (
                patch.object(sys, "pycache_prefix", str(prefix)),
                self.assertRaisesRegex(RuntimeError, "interrupted"),
                python_cache.temporary_directory(prefix="cache-fixture-") as directory,
            ):
                bytecode = Path(importlib.util.cache_from_source(str(directory / "module.py")))
                bytecode.parent.mkdir(parents=True, exist_ok=True)
                bytecode.write_bytes(b"temporary")
                raise RuntimeError("interrupted")
            self.assertFalse(bytecode.exists())
            self.assertFalse(directory.exists())
            self.assertEqual(shared.read_bytes(), b"shared")

    def run_clean(self, root: Path, scope: str) -> subprocess.CompletedProcess[str]:
        scripts = root / "scripts"
        scripts.mkdir(exist_ok=True)
        copy_file(
            ROOT / "scripts/repository/clean_cache.sh",
            scripts / "repository/clean_cache.sh",
        )
        return subprocess.run(
            [str(scripts / "repository/clean_cache.sh"), scope],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

    def populate_caches(self, root: Path) -> dict[str, Path]:
        caches = {
            "lake": root / "lean/.lake/cache",
            "tex": root / ".cache/latexindent/cache",
            "ruff": root / ".cache/ruff/cache",
            "py": root / ".cache/python/module.pyc",
            "mathlib": root / ".cache/mathlib/cache",
            "coverage": root / ".cache/coverage/.coverage",
            "hypothesis": root / ".hypothesis/examples/cache",
        }
        for path in caches.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("cache", encoding="utf-8")
        return caches

    def test_each_scope_removes_only_selected_cache(self) -> None:
        for scope in ("lake", "mathlib", "tex", "ruff", "py", "coverage", "hypothesis"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                caches = self.populate_caches(root)
                result = self.run_clean(root, scope)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(caches[scope].exists())
                self.assertTrue(all(path.exists() for name, path in caches.items() if name != scope))

    def test_all_removes_every_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caches = self.populate_caches(root)
            result = self.run_clean(root, "all")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(not path.exists() for path in caches.values()))

    def test_all_empties_mounted_roots_and_preserves_unrelated_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            caches = self.populate_caches(root)
            mounted = [root / "lean/.lake", root / ".hypothesis"]
            for directory in mounted:
                (directory / ".hidden").write_text("cache")
            preserved = root / ".cache/custom/keep"
            preserved.parent.mkdir(parents=True)
            preserved.write_text("keep")
            write_executable(
                root / "bin/mountpoint",
                '#!/bin/sh\ncase "$3" in\n  "$MOUNTED_LAKE"|"$MOUNTED_HYPOTHESIS") exit 0 ;;\n  *) exit 1 ;;\nesac\n',
            )
            with patch.dict(
                os.environ,
                {
                    "PATH": f"{root / 'bin'}:{os.environ['PATH']}",
                    "MOUNTED_LAKE": str(mounted[0]),
                    "MOUNTED_HYPOTHESIS": str(mounted[1]),
                },
            ):
                result = self.run_clean(root, "all")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(directory.is_dir() and not list(directory.iterdir()) for directory in mounted))
            self.assertTrue(all(not path.exists() for path in caches.values()))
            self.assertEqual(preserved.read_text(), "keep")

    def test_cleanup_preserves_unknown_caches_and_unrelated_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate_caches(root)
            preserved = (root / ".cache/custom/keep.pyc", root / "package/keep.pyc")
            for path in preserved:
                path.parent.mkdir(parents=True)
                path.write_text("keep")

            result = self.run_clean(root, "all")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(path.read_text() == "keep" for path in preserved))

    def test_hypothesis_scopes_clear_repository_examples_and_framework_cache(self) -> None:
        for scope in ("hypothesis", "all"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                examples = root / ".cache/hypothesis/examples/old-example"
                framework = root / ".hypothesis/constants/old-constant"
                preserved = root / ".cache/custom/keep"
                for path in (examples, framework, preserved):
                    path.parent.mkdir(parents=True)
                    path.write_text("cache")
                result = self.run_clean(root, scope)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(examples.exists())
                self.assertFalse(framework.exists())
                self.assertEqual(preserved.read_text(), "cache")

    def test_rejects_symlinked_cache_directories_and_parents(self) -> None:
        for relative, scope in ((".cache/ruff", "ruff"), ("lean/.lake", "lake")):
            for parent_link in (False, True):
                with (
                    self.subTest(relative=relative, parent_link=parent_link),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    root = Path(directory) / "repo"
                    root.mkdir()
                    external = Path(directory) / "external"
                    external.mkdir()
                    cache = root / relative
                    if parent_link:
                        cache.parent.symlink_to(external, target_is_directory=True)
                        external_cache = external / cache.name
                        external_cache.mkdir()
                    else:
                        cache.parent.mkdir()
                        cache.symlink_to(external, target_is_directory=True)
                        external_cache = external
                    sentinel = external_cache / "keep"
                    sentinel.write_text("keep")

                    result = self.run_clean(root, scope)

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("refusing symlinked cache path", result.stderr)
                    self.assertEqual(sentinel.read_text(), "keep")
                    self.assertTrue(cache.exists())

    def test_cleanup_does_not_follow_links_inside_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            cache = root / ".cache/ruff"
            cache.mkdir(parents=True)
            external = Path(directory) / "external"
            external.mkdir()
            sentinel = external / "keep"
            sentinel.write_text("keep")
            (cache / "link").symlink_to(external, target_is_directory=True)

            result = self.run_clean(root, "ruff")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(cache.exists())
            self.assertEqual(sentinel.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
