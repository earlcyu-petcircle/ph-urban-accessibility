"""The per-barangay summaries behind the comparison site agree with the whole-area ones."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "shared"))
sys.path.insert(0, str(REPO / "src" / "03_analyse"))

import measures


def test_group_quantile_matches_wquantile_within_each_group():
    rng = np.random.default_rng(7)
    keys = np.repeat(["a", "b", "c"], [5, 40, 200])
    values = rng.gamma(2.0, 300.0, keys.size)
    people = rng.uniform(0.2, 9.0, keys.size)
    for q in (0.1, 0.5, 0.9):
        got = measures.group_quantile(values, people, keys, q)
        for k in ("a", "b", "c"):
            want = measures.wquantile(values[keys == k], people[keys == k], q)[0]
            assert got[k] == np.float64(want)


def test_group_median_of_counts_is_the_step_median():
    keys = np.array(["x"] * 4 + ["y"] * 3)
    counts = np.array([0, 1, 1, 5, 2, 2, 9])
    people = np.array([1.0, 1.0, 1.0, 10.0, 1.0, 1.0, 1.0])
    got = measures.group_median(counts, people, keys)
    assert got["x"] == measures.wmedian(counts[:4], people[:4], step=True) == 5
    assert got["y"] == measures.wmedian(counts[4:], people[4:], step=True) == 2


def test_barangay_table_carries_every_research_question():
    """Every column the comparison table reads, on a toy city of two barangays."""
    rows = []
    for pcode, n, far in (("P1", 30, 200.0), ("P2", 20, 1500.0)):
        for i in range(n):
            row = {"pcode": pcode, "people": 1.0 + i % 3, "d_bus_jeepney": far / 2, "d_rail": far * 3}
            for c in measures.CATEGORIES:
                row[f"d_{c}"] = far + 10 * i
                for m in (5, 10, 15):
                    row[f"n_{c}_{m}"] = (i % 4) * (m // 5)
                if c in measures.M3_CATEGORIES:
                    row[f"a_{c}"] = 1.0 + i / n
            rows.append(row)
    bt = measures.barangay_table(pd.DataFrame(rows)).set_index("pcode")
    for c in measures.CATEGORIES:
        for col in (f"p10_min_{c}", f"p90_min_{c}", f"n5_{c}", f"n10_{c}", f"n15_{c}"):
            assert bt[col].notna().all(), col
        assert (bt[f"p10_min_{c}"] <= bt[f"min_{c}"]).all() and (bt[f"min_{c}"] <= bt[f"p90_min_{c}"]).all()
    # P1 walks 200-490 m (all nine within 15 minutes); P2 walks 1,500 m or more (none)
    assert bt.loc["P1", "share_all_nine"] == 1.0 and bt.loc["P2", "share_all_nine"] == 0.0
    # P1's median resident has nine services; everyone with fewer lives in P2
    p2_share = bt.loc["P2", "people"] / bt.people.sum()
    assert np.isclose(bt.loc["P1", "m4_metro_fewer"], p2_share)
    assert bt.loc["P2", "m4_metro_fewer"] == 0.0


def test_jollibee_table_per_barangay_and_metro():
    w = pd.DataFrame(
        {
            "pcode": ["a", "a", "a", "b", "b"],
            "people": [1.0, 1.0, 1.0, 2.0, 0.0],  # the empty building in b is ignored
            "d_jollibee": [70.0, 700.0, 1400.0, 2100.0, 0.0],  # 1, 10, 20 and 30 minutes at 4.2 km/h
            "n_jollibee_5": [1, 0, 0, 0, 9],
            "n_jollibee_10": [2, 1, 0, 0, 9],
            "n_jollibee_15": [3, 2, 1, 0, 9],
        }
    )
    t = measures.jollibee_table(w).set_index("pcode")
    assert t.loc["a", "min_jollibee"] == 10.0
    assert t.loc["a", "within10_jollibee"] == 2 / 3
    assert list(t.loc["a", ["n5_jollibee", "n10_jollibee", "n15_jollibee"]]) == [0, 1, 2]
    assert t.loc["b", "min_jollibee"] == 30.0
    assert t.loc["metro", "within10_jollibee"] == 2 / 5
    assert t.loc["metro", "n15_jollibee"] == 1
