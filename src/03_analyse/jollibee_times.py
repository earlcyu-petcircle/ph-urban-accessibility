#!/usr/bin/env python3
"""
Walking times from every origin to the Jollibee stores (data/work/jollibee.parquet), with the
same machinery as the nine services (walk_times.py): the nearest store by one multi-source
search, and the stores within 5, 10, 15 and 20 minutes and the E2SFCA access score (one per
store) by one search per store, read at the origin's node.

Jollibee is a service shown beside the nine but not counted in the 15-minute score
(NOT_IN_SCORE in src/shared/common.py), so this writes its own table and leaves
walk_times.parquet, the five measures and the score untouched.

  data/work/jollibee_times.parquet   one row per origin: origin_id, d_jollibee (metres to the
                                     nearest store), n_jollibee_5 ... n_jollibee_20, a_jollibee

Run after walk_times.py:  python src/03_analyse/jollibee_times.py
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import ROOT, THRESHOLDS_MIN, WORK, require
from walk_times import Network, counts_and_access, nearest_by_node


def main():
    require(WORK / "walk_times.parquet", how="Run src/03_analyse/walk_times.py first.")
    require(WORK / "jollibee.parquet", how="Run src/02_build_tables/build_jollibee.py first.")
    t0 = time.time()
    net = Network()
    # The origins as walk_times.py snapped them to the network
    origins = pd.read_parquet(WORK / "walk_times.parquet", columns=["origin_id", "people", "node", "hop_m"])
    jb = pd.read_parquet(WORK / "jollibee.parquet").assign(category="jollibee", in_default=True, group_capacity=np.nan)
    o_node, o_hop = origins.node.values, origins.hop_m.values

    out = origins[["origin_id"]].copy()
    nearest = nearest_by_node(net, {"jollibee": (jb.lon.values, jb.lat.values)})["jollibee"]
    out["d_jollibee"] = (nearest[o_node] + o_hop).astype("float32")
    pop_node = np.bincount(o_node, weights=origins.people.values, minlength=net.n)
    counts, scores = counts_and_access(net, jb, None, pop_node, categories=("jollibee",))
    for j, m in enumerate(THRESHOLDS_MIN):
        out[f"n_jollibee_{m}"] = counts["jollibee"][j][o_node].astype(np.int16)
    # E2SFCA access per 10,000 residents, scaled as walk_times.py scales the nine
    out["a_jollibee"] = (scores["jollibee"][o_node] * 10_000).astype("float32")
    out.to_parquet(WORK / "jollibee_times.parquet", index=False)
    print(
        f"wrote {(WORK / 'jollibee_times.parquet').relative_to(ROOT)}: {len(jb)} stores, "
        f"{len(out):,} origins ({time.time() - t0:.0f}s)"
    )


if __name__ == "__main__":
    main()
