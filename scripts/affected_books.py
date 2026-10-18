#!/usr/bin/env python3
"""Select manifest books whose PDF build inputs changed."""

from __future__ import annotations

import argparse
import json
import os

import book_impact
from impact_plan import pdf_selection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--format", choices=("json", "github"), default="json")
    args = parser.parse_args()
    paths = None if args.all else book_impact.changed_paths(args.base, args.head)
    requested = json.loads(os.environ.get("RELEASE_MATRIX", '{"book":[]}'))["book"]
    result = pdf_selection(paths, args.base, release_books=tuple(requested))

    if args.format == "github":
        print("matrix=" + json.dumps({"book": result["book"]}, separators=(",", ":")))
        print(f"count={result['count']}")
        print("site_changed=" + str(result["site_changed"]).lower())
        print("snapshot_changed=" + str(result["snapshot_changed"]).lower())
    else:
        print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
