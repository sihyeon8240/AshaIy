"""Container diagnostics preserve caches and reject foreign executables."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.toolchain import check_environment as ENVIRONMENT


class ContainerEnvironmentTests(unittest.TestCase):
    def test_foreign_native_cache_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "lean/.lake/packages/mathlib/.lake/build/bin/cache"
            cache.parent.mkdir(parents=True)
            header = bytearray(20)
            header[:6] = b"\x7fELF\x02\x01"
            header[18:20] = (62).to_bytes(2, "little")
            cache.write_bytes(header)
            with (
                patch.object(ENVIRONMENT.platform, "machine", return_value="aarch64"),
                patch.object(ENVIRONMENT.shutil, "which", return_value=None),
                patch.object(ENVIRONMENT.sys, "executable", str(cache)),
                patch.object(ENVIRONMENT, "ROOT", root),
                patch.object(ENVIRONMENT.subprocess, "run") as execute,
            ):
                errors = ENVIRONMENT.native_environment_errors(root)
                self.assertEqual(ENVIRONMENT.main(), 1)
                execute.assert_not_called()
            self.assertTrue(any("targets amd64, host is arm64" in error for error in errors), errors)
            self.assertTrue(any(str(cache) in error for error in errors), errors)
            self.assertEqual(cache.read_bytes(), header)
            header[18:20] = (183).to_bytes(2, "little")
            cache.write_bytes(header)
            with (
                patch.object(ENVIRONMENT.platform, "machine", return_value="aarch64"),
                patch.object(ENVIRONMENT.shutil, "which", return_value=None),
                patch.object(ENVIRONMENT.sys, "executable", str(cache)),
            ):
                self.assertEqual(ENVIRONMENT.native_environment_errors(root), [])


if __name__ == "__main__":
    unittest.main()
