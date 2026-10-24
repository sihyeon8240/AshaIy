"""Current-main alias promotion and authenticated/anonymous bootstrap boundaries."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import image_registry

IMAGE = "ghcr.io/example/toolchain@sha256:" + "a" * 64


class RegistryPromotionTests(unittest.TestCase):
    def test_only_current_main_advances_aliases_and_private_access_is_reported(self):
        for current, anonymous in ((True, True), (False, True), (True, False)):
            with self.subTest(current=current, anonymous=anonymous):
                calls = []

                def execute(*args, env=None):
                    calls.append(args)
                    if args[0] == "git":
                        return ("head" if current else "new") + "\trefs/heads/main"
                    if args[:3] == ("docker", "manifest", "inspect"):
                        assert env is not None
                        self.assertTrue(Path(env["DOCKER_CONFIG"]).is_dir())
                        if not anonymous:
                            raise subprocess.CalledProcessError(1, args)
                        return json.dumps(
                            {
                                "manifests": [
                                    {"platform": {"os": "linux", "architecture": arch}}
                                    for arch in ("amd64", "arm64")
                                ]
                            }
                        )
                    return ""

                with tempfile.TemporaryDirectory() as temporary:
                    summary = Path(temporary) / "summary"
                    with (
                        patch.dict(
                            os.environ,
                            {"GITHUB_SHA": "head", "GITHUB_STEP_SUMMARY": str(summary)},
                        ),
                        patch.object(
                            image_registry,
                            "load_image",
                            return_value=IMAGE.replace("a" * 64, "b" * 64),
                        ),
                        patch.object(image_registry, "command", side_effect=execute),
                        contextlib.redirect_stdout(io.StringIO()),
                    ):
                        image_registry.report(IMAGE)
                    promotion = [args for args in calls if "create" in args]
                    self.assertEqual(len(promotion), int(current))
                    if current:
                        self.assertEqual(promotion[0][-1], IMAGE)
                    text = summary.read_text()
                    self.assertIn("local pin differs", text)
                    self.assertIn(
                        "lookup succeeded" if anonymous else "lookup failed", text
                    )

    def test_registry_migration_never_updates_aliases(self):
        with (
            patch.object(image_registry, "load_image", return_value=IMAGE),
            patch.object(image_registry, "command") as execute,
            self.assertRaisesRegex(ValueError, "configured package"),
        ):
            image_registry.report(IMAGE.replace("example", "another"))
        execute.assert_not_called()
