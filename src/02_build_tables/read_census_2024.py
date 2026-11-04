#!/usr/bin/env python3
"""
Read the PSA 2024 Census of Population workbook for the National Capital Region, saved by
hand to data/manual/popcen2024/ncr.xlsx, and join its barangay counts to the COD-AB pcodes.

  data/work/census_2024.parquet          one row per Metro Manila barangay: pcode, people
  data/derived/census_2024_check.json    totals against the official NCR count, unmatched names

Not built yet: arrives in PR 2.
Run after 01_collect_data.sh:  python src/02_build_tables/read_census_2024.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=2)
