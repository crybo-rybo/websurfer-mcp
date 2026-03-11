"""Pytest configuration for src-layout imports."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"

src_root = str(SRC_ROOT)
if src_root not in sys.path:
    sys.path.insert(0, src_root)
