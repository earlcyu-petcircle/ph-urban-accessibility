#!/usr/bin/env python3
"""
The validation audits: a random 30 services per barangay checked against street imagery, the
DOH and DepEd registry match rates, and the street-imagery walk audit (about 20 routes in and
around each barangay scored for sidewalk, crossings, shade and obstruction), which also counts
sari-sari stores per kilometre.

  results/tables/service_audit.csv, results/tables/walk_audit.csv

Not built yet: arrives in PR 3.
Run after sensitivity.py:  python src/03_analyse/audits.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=3)
