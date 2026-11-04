#!/usr/bin/env python3
"""
A small range-aware web server for docs/, so the story site and the PMTiles map can be previewed
locally at http://localhost:8000/ (PMTiles do not open from file://).

Not built yet: arrives in PR 4.
Run after build_map_tiles.py:  python src/04_build_map/serve_map.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=4)
