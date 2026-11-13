"""
The ten sensitivity checks, and the robustness verdict.

Each check recomputes the headline metrics for the three barangays under one change of
assumption. The headline metrics are the median resident's walk to each of the nine categories
(M1), mean categories within 15 minutes (M4) and the share with convenient transit (M5).
A difference between two barangays counts as a finding only if their order on that metric is
the same in the base case and in every variant of every check that moves it.

  check_rows(w, net)     one row per check, variant, barangay and metric
  robustness(rows)       one row per metric and pair of barangays: does the order survive?

Check 04, the home lens, reads the private data/manual/homes.csv when it is there and writes its
results only to data/work/home_lens.csv (gitignored); the committed tables say whether it ran.
"""

import sys
from itertools import combinations
from pathlib import Path

import h3
import numpy as np
import pandas as pd
import rasterio
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import (
    BARANGAYS,
    CATEGORIES,
    CHECK_WALKSHED_MIN,
    COVERAGE_MIN,
    HOMES_FILE,
    THRESHOLDS_MIN,
    TRANSIT_HIGH_CAPACITY_M,
    TRANSIT_LOW_CAPACITY_M,
    WALK_SPEED_KMH,
    WALK_SPEEDS_SENSITIVITY_KMH,
    WORK,
    WORLDPOP_TIF,
    metres,
)
from measures import STUDY, minutes, wmean, wmedian
from walk_times import POINT_CATEGORIES, layer_points, load_services, transit_points, xy

METRICS = [f"M1 {c}" for c in CATEGORIES] + ["M4", "M5"]
LOWER_IS_BETTER = {m: m.startswith("M1") for m in METRICS}
CHECKS = {
    "base": "Base case",
    "01": "Walking speed",
    "02": "Time threshold",
    "03": "Study area",
    "04": "Home lens",
    "05": "Distance type",
    "06": "Origin resolution",
    "07": "Service source",
    "08": "Overture confidence",
    "09": "Population surface",
    "10": "Jeepney rule",
}


def headline(d, people, dist, speed_kmh=WALK_SPEED_KMH, cover_min=COVERAGE_MIN):
    """The eleven headline metrics for one set of origins.

    dist: {category: metres per origin} plus 'bus_jeepney' and 'rail' for M5."""
    out = {f"M1 {c}": minutes(wmedian(dist[c], people), speed_kmh) for c in CATEGORIES}
    lim = metres(cover_min, speed_kmh)
    out["M4"] = wmean(sum((dist[c] <= lim).astype(int) for c in CATEGORIES), people)
    convenient = (dist["bus_jeepney"] <= TRANSIT_LOW_CAPACITY_M) | (dist["rail"] <= TRANSIT_HIGH_CAPACITY_M)
    out["M5"] = wmean(convenient, people)
    return out


def base_dist(d):
    out = {c: d[f"d_{c}"].values for c in CATEGORIES}
    out["bus_jeepney"], out["rail"] = d.d_bus_jeepney.values, d.d_rail.values
    return out


def node_dist(arrays, node, hop, layer="merged", transit="merged:transit", bus="m5:bus_jeepney"):
    """Distances for origins at `node` with `hop`, from the saved node arrays of one layer."""
    out = {}
    for c in CATEGORIES:
        key = f"{layer}:{c}" if c in POINT_CATEGORIES else f"merged:{c}"
        out[c] = arrays[key][node] + hop
    out["transit"] = arrays[transit][node] + hop
    out["bus_jeepney"] = arrays[bus][node] + hop
    out["rail"] = arrays["m5:rail"][node] + hop
    return out


def check_rows(w, net):
    arrays = dict(np.load(WORK / "nearest_nodes.npz"))
    rows = []

    def add(check, variant, name, metrics):
        for metric, value in metrics.items():
            rows.append(
                {
                    "check": check,
                    "check_name": CHECKS[check],
                    "variant": variant,
                    "barangay": name,
                    "metric": metric,
                    "value": value,
                }
            )

    study = {name: w[w.study.eq(name)] for name in STUDY}
    for name, d in study.items():
        add("base", "base", name, headline(d, d.people, base_dist(d)))

    # 01 walking speed and 02 time threshold
    for name, d in study.items():
        for s in WALK_SPEEDS_SENSITIVITY_KMH:
            if s != WALK_SPEED_KMH:
                add("01", f"{s} km/h", name, headline(d, d.people, base_dist(d), speed_kmh=s))
        for m in THRESHOLDS_MIN:
            if m != COVERAGE_MIN:
                add("02", f"{m} min", name, {"M4": headline(d, d.people, base_dist(d), cover_min=m)["M4"]})

    # 03 equal walk-sheds round each barangay's population-weighted centre
    for name, d in study.items():
        cx, cy = np.average(xy(d.lon, d.lat), axis=0, weights=d.people)
        centre, _ = net.tree.query([cx, cy])
        reach = net.within(np.array([centre]), metres(max(CHECK_WALKSHED_MIN)))[0]
        for m in CHECK_WALKSHED_MIN:
            inside = w[(reach[w.node.values] + w.hop_m.values) <= metres(m)]
            add("03", f"{m}-min walk-shed", name, headline(inside, inside.people, base_dist(inside)))

    # 04 the home lens: private, written only to data/work/
    if HOMES_FILE.exists():
        homes = pd.read_csv(HOMES_FILE, dtype={"pcode": str})
        private = []
        for _, h in homes.iterrows():
            name = BARANGAYS.get(h.pcode, {}).get("name")
            if name is None:
                continue
            node, hop = net.snap([h.lon], [h.lat])
            reach = net.within(node, metres(15))[0]
            inside = w[(reach[w.node.values] + w.hop_m.values) <= metres(15)]
            for metric, value in headline(inside, inside.people, base_dist(inside)).items():
                private.append({"barangay": name, "metric": metric, "value": value})
        pd.DataFrame(private).to_csv(WORK / "home_lens.csv", index=False)
    home_lens_ran = HOMES_FILE.exists()

    # 05 straight line instead of the street network
    svc = load_services()
    access = pd.read_parquet(WORK / "open_space_access.parquet")
    routes = pd.read_parquet(WORK / "transit_routes.parquet").drop_duplicates("node_id")
    pts = layer_points(svc, access, routes)
    pts.update(transit_points(svc, routes))
    trees = {k: cKDTree(xy(*v)) for k, v in pts.items()}
    for name, d in study.items():
        oxy = xy(d.lon, d.lat)
        straight = {k: t.query(oxy)[0] for k, t in trees.items()}
        add("05", "straight line", name, headline(d, d.people, straight))

    # 06 origin resolution: 100 m WorldPop cells and H3 resolution-9 cells, at their centres
    with rasterio.open(WORLDPOP_TIF) as src:
        x0, res_x, y0, res_y = src.transform.c, src.transform.a, src.transform.f, src.transform.e
    for name, d in study.items():
        col = np.floor((d.lon.values - x0) / res_x)
        row = np.floor((d.lat.values - y0) / res_y)
        cells = pd.DataFrame({"lon": x0 + (col + 0.5) * res_x, "lat": y0 + (row + 0.5) * res_y, "people": d.people})
        cells = cells.groupby(["lon", "lat"], as_index=False).people.sum()
        hexes = d.groupby("h3_9", as_index=False).people.sum()
        ll = np.array([h3.cell_to_latlng(c) for c in hexes.h3_9])
        hexes["lat"], hexes["lon"] = ll[:, 0], ll[:, 1]
        for variant, o in (("100 m cells", cells), ("H3 resolution 9", hexes)):
            node, hop = net.snap(o.lon, o.lat)
            add("06", variant, name, headline(o, o.people.values, node_dist(arrays, node, hop)))

    # 07 service source, 08 Overture confidence, 10 the jeepney rule (from the saved node arrays)
    for name, d in study.items():
        node, hop = d.node.values, d.hop_m.values
        for layer, check, variant in (
            ("overture", "07", "Overture only"),
            ("osm", "07", "OpenStreetMap only"),
            ("conf_0.3", "08", "confidence 0.3"),
            ("conf_0.7", "08", "confidence 0.7"),
        ):
            add(check, variant, name, headline(d, d.people, node_dist(arrays, node, hop, layer=layer)))
        stops = node_dist(arrays, node, hop, transit="stops_only:transit", bus="m5:bus_jeepney_stops_only")
        add("10", "mapped stops only", name, headline(d, d.people, stops))

    # 09 population surface
    for name, d in study.items():
        add("09", "GHS-POP", name, headline(d, d.people_ghs, base_dist(d)))

    out = pd.DataFrame(rows)
    out.attrs["home_lens_ran"] = home_lens_ran
    return out


def robustness(rows, tolerance=0.05):
    """Per metric and pair: the base difference, and whether every variant keeps its sign.

    A difference smaller than `tolerance` (0.05 minutes or categories; one percentage point for
    M5's share) counts as a tie, and a tie is not a finding."""
    out = []
    piv = rows.pivot_table(index=["check", "variant", "metric"], columns="barangay", values="value")
    for metric in METRICS:
        m = piv.xs(metric, level="metric")
        base = m.loc[("base", "base")]
        tol = tolerance if metric != "M5" else 0.01
        for a, b in combinations(STUDY, 2):
            diff = base[a] - base[b]
            sign = 0 if abs(diff) < tol else np.sign(diff)
            flips = []
            for (check, variant), r in m.drop(index=("base", "base")).iterrows():
                if pd.isna(r[a]) or pd.isna(r[b]):
                    continue
                d = r[a] - r[b]
                s = 0 if abs(d) < tol else np.sign(d)
                if s != sign:
                    flips.append(f"{check} {variant} ({'tie' if s == 0 else 'reversed'})")
            better = None
            if sign != 0:
                a_better = (diff < 0) == LOWER_IS_BETTER[metric]
                better = a if a_better else b
            out.append(
                {
                    "metric": metric,
                    "a": a,
                    "b": b,
                    "value_a": base[a],
                    "value_b": base[b],
                    "better_in_base": better or "tie",
                    "survives": sign != 0 and not flips,
                    "never_reversed": sign != 0 and not any(f.endswith("(reversed)") for f in flips),
                    "variants_that_change_it": "; ".join(flips),
                }
            )
    return pd.DataFrame(out)
