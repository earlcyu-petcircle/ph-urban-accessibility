#!/usr/bin/env python3
"""
Walking times along the network: one multi-source shortest-path run per service category
gives every node its time to the nearest service, and a second pass counts services within 5,
10, 15 and 20 minutes, at WALK_SPEED_KMH and at each sensitivity speed.

  data/work/walk_times.parquet   one row per origin and category

Not built yet: arrives in PR 3.
Run after 02_build_tables.sh:  python src/03_analyse/walk_times.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=3)
