#!/usr/bin/env python3
"""Portable wrapper that runs the installed token_saver package or bundled fallback."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from token_saver.cli import main
except ImportError:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "token_saver" / "cli.py").exists():
            sys.path.insert(0, str(parent))
            break
    from token_saver.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
