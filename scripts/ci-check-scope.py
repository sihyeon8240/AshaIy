#!/usr/bin/env python3
"""Keep Lean checks unless changes are known to leave proof checking untouched."""

from __future__ import annotations

import argparse

from ci_changes import changed_paths
from impact_plan import source_selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="")
    parser.add_argument("--format", choices=("lean", "github"), default="lean")
    arguments = parser.parse_args()

    paths = changed_paths(arguments.base)
    selections = source_selection(paths, arguments.base)
    print(f"lean={str(selections['lean']['selected']).lower()}")
    if arguments.format == "github":
        for key, selection in selections.items():
            if key != "lean":
                print(f"{key}={str(selection['selected']).lower()}")


if __name__ == "__main__":
    main()
