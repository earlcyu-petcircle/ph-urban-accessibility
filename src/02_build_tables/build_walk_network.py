#!/usr/bin/env python3
"""
Build the OpenStreetMap walking network for Metro Manila plus the fringe: every way a
pedestrian may use, walkable in both directions, largest connected component; expressways out,
footbridges and stairs in.

  data/work/walk_nodes.parquet, data/work/walk_edges.parquet

Not built yet: arrives in PR 2.
Run after build_services.py:  python src/02_build_tables/build_walk_network.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import not_built

not_built(__file__, pr=2)
