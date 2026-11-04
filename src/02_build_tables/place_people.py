#!/usr/bin/env python3
"""
Place people in buildings: each barangay's 2024 census count spread over its WorldPop 2024
100 m cells, then over the residential building footprints in each cell.

  data/work/origins.parquet   one row per residential building: pcode, people, location

Every residential building in the three study barangays becomes an origin weighted by its
people; the rest of Metro Manila gives the context percentiles.

Not built yet: arrives in PR 2.
Run after read_census_2024.py:  python src/02_build_tables/place_people.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=2)
