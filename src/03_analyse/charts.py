#!/usr/bin/env python3
"""
The static figures: each barangay's profile of the five measures, the share of residents within
each threshold, and the metro context.

  results/figures/

Not built yet: arrives in PR 3.
Run after audits.py:  python src/03_analyse/charts.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=3)
