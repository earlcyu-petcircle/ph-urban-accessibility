#!/usr/bin/env python3
"""
The web map's vector tiles: H3 resolution-10 access hexagons for all of Metro Manila, the three
study barangays and their check walk-sheds, services by category and source, and transit, as
PMTiles built with tippecanoe. Home locations are never written.

  docs/map/data/*.pmtiles

Not built yet: arrives in PR 4.
Run after 03_analyse.sh:  python src/04_build_map/build_map_tiles.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=4)
