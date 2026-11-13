"""The per-barangay summaries behind the comparison site agree with the whole-area ones."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "shared"))
sys.path.insert(0, str(REPO / "src" / "03_analyse"))

import measures
from common import SHOWN


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
    bt = measures.barangay_table(toy_city(measures.CATEGORIES)).set_index("pcode")
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


def toy_city(services):
    """Two barangays: P1 walks 200-490 m to everything, P2 1,500 m or more."""
    rows = []
    for pcode, n, far in (("P1", 30, 200.0), ("P2", 20, 1500.0)):
        for i in range(n):
            row = {"pcode": pcode, "people": 1.0 + i % 3, "d_bus_jeepney": far / 2, "d_rail": far * 3}
            for c in services:
                row[f"d_{c}"] = far + 10 * i
                for m in (5, 10, 15):
                    row[f"n_{c}_{m}"] = (i % 4) * (m // 5)
                if c in measures.CROWDING:
                    row[f"a_{c}"] = 1.0 + i / n
            rows.append(row)
    return pd.DataFrame(rows)


def test_a_service_outside_the_score_gets_every_answer_but_never_moves_the_score():
    w = toy_city(SHOWN)
    nine = measures.barangay_table(w).set_index("pcode")
    shown = measures.barangay_table(w, services=SHOWN).set_index("pcode")
    # Jollibee walks, counts, spread, Metro Manila rank and crowding, like any of the nine
    for col in ("min", "p10_min", "p90_min", "within10", "n5", "n10", "n15", "metro_longer", "m3_index"):
        assert shown[f"{col}_jollibee"].notna().all(), col
    assert "min_jollibee" not in nine
    # ... while the score, its rank and the categories within 15 minutes are the nine's alone
    for col in ("m4_mean", "score", "share_all_nine", "m4_metro_fewer", "score_rank"):
        pd.testing.assert_series_equal(shown[col], nine[col])
    # Moving every Jollibee next door leaves the score where it was
    w.loc[:, "d_jollibee"] = 0.0
    pd.testing.assert_series_equal(measures.barangay_table(w, services=SHOWN).set_index("pcode").score, nine.score)


def test_service_stats_agrees_with_the_barangay_figures():
    w = toy_city(SHOWN)
    stats = measures.service_stats(w, "jollibee")
    all_people = measures.barangay_table(w.assign(pcode="all"), services=SHOWN).set_index("pcode").loc["all"]
    assert np.isclose(stats["M1", "median_min"], all_people.min_jollibee, atol=0.15)
    assert np.isclose(stats["M1", "share_within_10min"], all_people.within10_jollibee)
    assert stats["M2", "median_within_10min"] == all_people.n10_jollibee
    assert ("M3", "median_per_10k") in stats and ("M3", "median_per_10k") not in measures.service_stats(w, "transit")
