#!/usr/bin/env python3
"""Command-line adapter for check_architecture.py."""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.architecture_checks import main

if __name__ == "__main__":
    raise SystemExit(main())
