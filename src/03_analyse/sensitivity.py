#!/usr/bin/env python3
"""
The ten sensitivity checks in docs/paper.md (section 4.5): walking speed, threshold, study area,
the private home lens, distance type, origin resolution, service source, Overture confidence,
population surface and the jeepney rule. A difference between the barangays is reported as a
finding only if their ordering survives these.

  results/tables/sensitivity.csv

Not built yet: arrives in PR 3.
Run after measures.py:  python src/03_analyse/sensitivity.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=3)
