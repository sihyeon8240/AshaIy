"""Render an opt-in tagging specimen in a disposable TeX user tree."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.repository.config.repository_config import ROOT, load_toolchain


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-missing", action="store_true", help="install tagging packages only into build/tagging-texmf"
    )
    arguments = parser.parse_args()
    output = ROOT / "build/tagging-probe"
    tree = ROOT / "build/tagging-texmf"
    output.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, "TEXMFHOME": str(tree)}
    result = {"schema_version": 1, "conformance": "not assessed", "compiled": False, "tagged": False}
    try:
        if arguments.install_missing:
            tree.mkdir(parents=True, exist_ok=True)
            if not (tree / "tlpkg/texlive.tlpdb").exists():
                subprocess.run(["tlmgr", "--usermode", "--usertree", str(tree), "init-usertree"], check=True)
            archive = load_toolchain()["TEXLIVE_ARCHIVE_DATE"]
            subprocess.run(
                [
                    "tlmgr",
                    "--usermode",
                    "--usertree",
                    str(tree),
                    "--repository",
                    f"https://texlive.info/tlnet-archive/{archive}/tlnet",
                    "install",
                    "latex-lab",
                    "tagpdf",
                    "pdfmanagement",
                ],
                check=True,
                timeout=300,
            )
        source = ROOT / "tests/fixtures/tagged-mathematics.tex"
        with (output / "console.log").open("w") as log:
            subprocess.run(
                ["bash", str(ROOT / "scripts/latex/build_vscode.sh"), str(output), str(source)],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=180,
            )
        result["compiled"] = True
        checked = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/latex/check_log.py"),
                "--strict",
                str(output / "tagged-mathematics.log"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        result["strict_log"] = checked.returncode == 0
        result["diagnostic"] = checked.stdout + checked.stderr
        result["tagging_warnings"] = re.findall(
            r"Package tagpdf Warning:.*?(?=\n\n|\Z)",
            (output / "tagged-mathematics.log").read_text(),
            re.DOTALL,
        )
        info = subprocess.check_output(["pdfinfo", str(output / "tagged-mathematics.pdf")], text=True)
        result["tagged"] = any(line.startswith("Tagged:") and line.split()[-1] == "yes" for line in info.splitlines())
        result["manual_review"] = (
            "Review headings, math semantics, code reading order, bibliography and assistive technology output."
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result["error"] = str(error)
        print(
            "See build/tagging-probe/console.log; --install-missing prepares the isolated pinned user tree.",
            file=sys.stderr,
        )
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Saved tagging experiment: {output / 'result.json'}")
    return int(not (result["compiled"] and result["tagged"] and result.get("strict_log")))


if __name__ == "__main__":
    raise SystemExit(main())
