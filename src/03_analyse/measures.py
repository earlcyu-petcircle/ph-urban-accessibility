#!/usr/bin/env python3
"""
The five measures per origin, then summarised per barangay over residents:
M1 nearest walk, M2 choice (counts within 5, 10 and 15 minutes), M3 crowding-adjusted supply
(E2SFCA, 15-minute catchment), M4 15-minute coverage of the nine categories, and M5 transit
access after UN SDG 11.2.1 (500 m to a bus or jeepney stop or route, 1 km to rail).

  results/tables/measures_by_barangay.csv, results/tables/metro_percentiles.csv

Not built yet: arrives in PR 3.
Run after walk_times.py:  python src/03_analyse/measures.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=3)
