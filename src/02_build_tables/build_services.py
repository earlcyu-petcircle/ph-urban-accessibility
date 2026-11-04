#!/usr/bin/env python3
"""
Build the nine-category service layer (CATEGORIES in src/shared/common.py) from Overture
places and OpenStreetMap: drop closed places and Overture confidence below 0.5, merge
duplicates within 50 m that share a category or name, and match public health facilities and
schools to the DOH and DepEd registries.

  data/work/services.parquet           one row per service: category, source, location
  data/derived/service_quality.csv     counts by source and registry match rates by barangay

Sari-sari stores are almost absent from both sources; the few mapped ones stay in food retail
(docs/paper.md, section 8).

Not built yet: arrives in PR 2.
Run after place_people.py:  python src/02_build_tables/build_services.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=2)
