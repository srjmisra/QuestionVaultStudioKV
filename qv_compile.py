#!/usr/bin/env python3
"""Convenience launcher so ``python qv_compile.py`` works without installing the package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from compiler_engine.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
