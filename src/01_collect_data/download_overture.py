#!/usr/bin/env python3
"""
Download Overture Maps places and buildings for Metro Manila plus the 2 km fringe
(release OVERTURE_RELEASE in src/shared/common.py) into data/raw/ as GeoParquet, with the
official overturemaps downloader.

  data/raw/overture_places.parquet      every place with its category and confidence
  data/raw/overture_buildings.parquet   footprints, for placing people in 02_build_tables

Not built yet: arrives in PR 2.
Run after download_sources.sh:  python src/01_collect_data/download_overture.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=2)
