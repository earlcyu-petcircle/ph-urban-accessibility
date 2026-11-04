#!/usr/bin/env python3
"""
Build the small committed tables the paper cites, and the numbers behind docs/data-quality.md.

  data/derived/barangays.csv      one row per Metro Manila barangay: people, area, density, study flag
  data/derived/data_quality.json  row counts, licences and completeness for every layer

Not built yet: arrives in PR 2.
Run after build_walk_network.py:  python src/02_build_tables/build_tables.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=2)
