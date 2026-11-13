#!/usr/bin/env python3
"""
Vector tiles and small files for the interactive web map in docs/map/ (MapLibre GL JS reading
PMTiles). Everything is built from the analysis results (03_analyse.sh); nothing new is measured.

  docs/map/data/hexes.pmtiles      H3 resolution-10 hexagons with residents: people, and for
                                   each category the median resident's walk in metres (M1),
                                   services within 5, 10, 15 and 20 minutes (M2) and the share of
                                   Metro Manila residents with a longer walk; categories within
                                   each time at 3.6, 4.2 and 4.8 km/h (M4); the share with
                                   convenient transit (M5)
  docs/map/data/services.pmtiles   the default service layer: category, kind, sources, name
  docs/map/data/transit.pmtiles    LRT and MRT lines, and every mapped bus and jeepney route
  docs/map/data/barangays.pmtiles  Metro Manila's barangay and city outlines, with people and M4
  docs/map/data/study.geojson      the three barangays and their 10, 15 and 20-minute walk-sheds
  docs/map/data/jollibee.geojson   the Jollibee stores, a tracked layer outside the nine services
  docs/map/data/barangays.json     every barangay's answers to the five research questions, with
                                   its people, land area and density, and its walk to Jollibee,
                                   for the picks table
  docs/map/data/summary.json       the example picks and Metro Manila's figures for the same rows

Privacy: no building or home is published. Hexagons hold 34 residential buildings at the median;
those with fewer than MIN_BUILDINGS are left off the map (their residents still count in every
statistic), and walk-sheds are drawn round each barangay's population-weighted centre, which is
a street node, not a home.

Needs tippecanoe on the path (brew install tippecanoe).
Run after 03_analyse.sh:  ./04_build_map.sh  or  python src/04_build_map/build_map_tiles.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import h3
import numpy as np
import osmium
import pandas as pd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "03_analyse"))  # the analysis functions

from common import (
    BARANGAYS,
    CATEGORIES,
    CHECK_WALKSHED_MIN,
    MAP_DATA,
    OSM_PBF,
    ROOT,
    STUDY_BOX,
    TABLES,
    THRESHOLDS_MIN,
    TRANSIT_HIGH_CAPACITY_M,
    TRANSIT_LOW_CAPACITY_M,
    UTM,
    WALK_SPEEDS_SENSITIVITY_KMH,
    WORK,
    metres,
    read_ncr_barangays,
    require,
)
from map_layers import CODES
from measures import M3_CATEGORIES, barangay_table, coverage, jollibee_table, load
from walk_times import Network, xy

MIN_BUILDINGS = 5
TIPPECANOE = shutil.which("tippecanoe")
if TIPPECANOE is None:
    sys.exit("build_map_tiles.py needs tippecanoe on the path: brew install tippecanoe")
require(
    WORK / "walk_times.parquet",
    WORK / "jollibee_times.parquet",
    TABLES / "measures.csv",
    how="Run ./03_analyse.sh first.",
)
MAP_DATA.mkdir(parents=True, exist_ok=True)


def tippecanoe(gdf, name, layer, *args):
    src = WORK / f"map_{layer}.geojsons"
    gdf.to_file(src, driver="GeoJSONSeq")
    dst = MAP_DATA / name
    subprocess.run(
        [TIPPECANOE, "-o", str(dst), "--force", "-l", layer, "--quiet", "--no-tile-size-limit", *args, str(src)],
        check=True,
    )
    return dst.stat().st_size


def wsum(values, people, keys):
    """People-weighted mean of `values` within each key."""
    s = pd.DataFrame({"k": keys, "v": values * people, "p": people}).groupby("k").sum()
    return s.v / s.p


sizes = {}
w, b = load()

# ---------------------------------------------------------------------------
# 1. Hexagons
# ---------------------------------------------------------------------------
hexes = w.groupby("h3_10").agg(people=("people", "sum"), buildings=("people", "size"))
props = {}
for c in CATEGORIES:
    code = CODES[c]
    # The median resident's walk in each hexagon
    d = w[["h3_10", "people", f"d_{c}"]].sort_values(["h3_10", f"d_{c}"])
    d["cum"] = d.groupby("h3_10").people.cumsum()
    d["half"] = d.h3_10.map(hexes.people) / 2
    med = d[d.cum >= d.half].drop_duplicates("h3_10").set_index("h3_10")[f"d_{c}"]
    props[f"d_{code}"] = (med / 10).round() * 10
    # The share of Metro Manila residents with a longer walk than that median
    order = np.argsort(w[f"d_{c}"].values)
    xs, cw = w[f"d_{c}"].values[order], np.cumsum(w.people.values[order])
    longer = 1 - np.r_[0, cw][np.searchsorted(xs, med.values, side="right")] / cw[-1]
    props[f"p_{code}"] = pd.Series(np.round(longer * 100), index=med.index)
    for m in THRESHOLDS_MIN:
        props[f"n_{code}_{m}"] = wsum(w[f"n_{c}_{m}"].values.astype(float), w.people.values, w.h3_10.values).round()
for s in WALK_SPEEDS_SENSITIVITY_KMH:
    for m in THRESHOLDS_MIN:
        cov = coverage(w, minutes_=m, speed_kmh=s).values.astype(float)
        props[f"m4_{int(s * 10)}_{m}"] = wsum(cov, w.people.values, w.h3_10.values).round(1)
convenient = ((w.d_bus_jeepney <= TRANSIT_LOW_CAPACITY_M) | (w.d_rail <= TRANSIT_HIGH_CAPACITY_M)).astype(float)
props["m5"] = (wsum(convenient.values, w.people.values, w.h3_10.values) * 100).round()
hexes = hexes.join(pd.DataFrame(props))
shown = hexes[(hexes.buildings >= MIN_BUILDINGS) & (hexes.people >= 0.5)].copy()
shown["people"] = shown.people.round()
shown = shown.drop(columns="buildings")
for col in shown.columns:
    if col.startswith(("d_", "p_", "m5")) or col == "people":
        shown[col] = shown[col].astype(int)
geom = [shapely.Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(h)]) for h in shown.index]
hg = gpd.GeoDataFrame(shown.reset_index().rename(columns={"h3_10": "h3"}), geometry=geom, crs=4326)
sizes["hexes.pmtiles"] = tippecanoe(
    hg,
    "hexes.pmtiles",
    "hexes",
    "-Z11",
    "-z14",
    "--no-feature-limit",
    "--no-tiny-polygon-reduction",
    "--detect-shared-borders",
    "--coalesce-densest-as-needed",
)
left_off = hexes[(hexes.buildings < MIN_BUILDINGS) & (hexes.people >= 0.5)]
print(
    f"hexagons: {len(shown):,} shown, {len(left_off):,} with fewer than {MIN_BUILDINGS} buildings left off "
    f"({left_off.people.sum():,.0f} people, {left_off.people.sum() / hexes.people.sum():.1%})"
)

# ---------------------------------------------------------------------------
# 2. Services: the default layer, inside the study box
# ---------------------------------------------------------------------------
svc = pd.read_parquet(WORK / "services.parquet")
svc = svc[svc.in_default].copy()
svc["cat"] = svc.category.map(CODES)
svc["sources"] = svc.sources_in_group.str.replace("osm", "OpenStreetMap").str.replace("overture", "Overture")
svc["sources"] = svc.sources.str.replace("deped", "DepEd").str.replace(";", ", ")
svc["name"] = svc.name.fillna("")
sg = gpd.GeoDataFrame(svc[["cat", "kind", "sources", "name"]], geometry=gpd.points_from_xy(svc.lon, svc.lat), crs=4326)
sizes["services.pmtiles"] = tippecanoe(sg, "services.pmtiles", "services", "-Z11", "-z16", "-r1", "--no-feature-limit")

# Jollibee stores: tracked context, drawn as their own layer
jb = pd.read_parquet(WORK / "jollibee.parquet")
jg = gpd.GeoDataFrame({"name": jb.name.fillna("Jollibee")}, geometry=gpd.points_from_xy(jb.lon, jb.lat), crs=4326)
jg["geometry"] = jg.geometry.set_precision(1e-6)
(MAP_DATA / "jollibee.geojson").write_text(jg.to_json(drop_id=True) + "\n")

# ---------------------------------------------------------------------------
# 3. Transit lines: LRT and MRT, and every mapped bus and jeepney route, from the OSM extract
# ---------------------------------------------------------------------------
W_, S_, E_, N_ = STUDY_BOX
routes = pd.read_parquet(WORK / "transit_routes.parquet")
mode_of_way = routes.groupby("way_id").mode.agg(lambda m: "jeepney" if "jeepney" in set(m) else "bus").to_dict()
rail_ways = set()
for r in osmium.FileProcessor(str(OSM_PBF), osmium.osm.RELATION).with_filter(
    osmium.filter.TagFilter(("type", "route"))
):
    if r.tags.get("network") in ("Manila LRT", "Manila MRT") and r.tags.get("route") in ("light_rail", "subway"):
        rail_ways |= {m.ref for m in r.members if m.type == "w" and not m.role.startswith("platform")}
lines = []
fp = osmium.FileProcessor(str(OSM_PBF), osmium.osm.NODE | osmium.osm.WAY).with_locations()
for obj in fp.with_filter(osmium.filter.KeyFilter("highway", "railway")):
    if not obj.is_way() or (obj.id not in mode_of_way and obj.id not in rail_ways):
        continue
    pts = [(n.location.lon, n.location.lat) for n in obj.nodes if n.location.valid()]
    if len(pts) < 2 or not any(W_ <= x <= E_ and S_ <= y <= N_ for x, y in pts):
        continue
    lines.append(("rail" if obj.id in rail_ways else mode_of_way[obj.id], shapely.LineString(pts)))
tg = gpd.GeoDataFrame({"mode": [m for m, _ in lines]}, geometry=[g for _, g in lines], crs=4326)
stations = svc[svc.kind.eq("rail_station")]
tg = pd.concat(
    [
        tg,
        gpd.GeoDataFrame(
            {"mode": "station", "name": stations.name.values},
            geometry=gpd.points_from_xy(stations.lon, stations.lat),
            crs=4326,
        ),
    ]
)
sizes["transit.pmtiles"] = tippecanoe(tg, "transit.pmtiles", "transit", "-Z9", "-z16", "--no-feature-limit")
print(f"transit: {tg['mode'].value_counts().to_dict()}")

# ---------------------------------------------------------------------------
# 4. Every barangay: its measures (for the comparison panel and search) and its outline
# ---------------------------------------------------------------------------
geo = read_ncr_barangays(columns=["adm4_pcode"]).rename(columns={"adm4_pcode": "pcode"})
bt = barangay_table(w)
jt = jollibee_table(w.merge(pd.read_parquet(WORK / "jollibee_times.parquet"), on="origin_id", validate="1:1"))
jb_metro = jt.set_index("pcode").loc["metro"]
bt = bt.merge(jt[jt.pcode.ne("metro")], on="pcode", how="left", validate="1:1")
bt = b[["pcode", "barangay", "city", "area_km2", "people_per_km2"]].merge(bt, on="pcode", how="left")
bt.to_csv(MAP_DATA / "barangay_measures.csv", index=False, float_format="%.4g")
bbox = geo.set_index("pcode").bounds.round(5)
records = []
for r in bt.itertuples(index=False):
    if pd.isna(r.people):
        continue
    v = r._asdict()
    records.append(
        {
            "p": r.pcode,
            "n": r.barangay,
            "c": r.city,
            "pop": int(round(r.people)),
            "a": round(r.area_km2, 3),
            "d": int(r.people_per_km2),
            "s": round(r.score, 1),
            "rank": int(r.score_rank),
            "m4": round(r.m4_mean, 2),
            "a9": round(r.share_all_nine * 100),
            "q4": round(r.m4_metro_fewer * 100),
            "min": {CODES[c]: round(v[f"min_{c}"], 1) for c in CATEGORIES},
            "r": {CODES[c]: [round(v[f"p10_min_{c}"], 1), round(v[f"p90_min_{c}"], 1)] for c in CATEGORIES},
            "k": {CODES[c]: [int(v[f"n{m}_{c}"]) for m in (5, 10, 15)] for c in CATEGORIES},
            "w10": {CODES[c]: round(v[f"within10_{c}"] * 100) for c in CATEGORIES},
            "q": {CODES[c]: round(v[f"metro_longer_{c}"] * 100) for c in CATEGORIES},
            "x": {CODES[c]: round(v[f"m3_index_{c}"], 2) for c in M3_CATEGORIES},
            "t": [
                round(r.share_bus_jeepney_500m * 100),
                round(r.share_rail_1km * 100),
                round(r.share_convenient * 100),
            ],
            "b": list(bbox.loc[r.pcode]),
            # Jollibee, tracked context: minutes to the nearest, % within 10 minutes, counts within 5, 10, 15
            "jb": {
                "min": round(r.min_jollibee, 1),
                "w10": round(r.within10_jollibee * 100),
                "k": [int(v[f"n{m}_jollibee"]) for m in (5, 10, 15)],
            },
        }
    )
(MAP_DATA / "barangays.json").write_text(json.dumps(records, separators=(",", ":")) + "\n")
bg = geo.merge(
    bt[["pcode", "barangay", "city", "people", "score", *[f"min_{c}" for c in CATEGORIES], "share_convenient"]],
    on="pcode",
)
bg = bg.rename(columns={f"min_{c}": f"d_{CODES[c]}" for c in CATEGORIES} | {"share_convenient": "m5"})
for c in CATEGORIES:
    bg[f"d_{CODES[c]}"] = bg[f"d_{CODES[c]}"].round(1)
bg["score"] = bg.score.round(1)
bg["m5"] = (bg.m5 * 100).round()
bg["people"] = bg.people.round()
bg["kind"] = "barangay"
bg["geometry"] = bg.to_crs(UTM).simplify(3, preserve_topology=True).to_crs(4326)
cities = bg.dissolve("city", as_index=False)[["city", "geometry"]].assign(kind="city")
sizes["barangays.pmtiles"] = tippecanoe(
    gpd.GeoDataFrame(pd.concat([bg, cities]), crs=4326),
    "barangays.pmtiles",
    "barangays",
    "-Z9",
    "-z15",
    "--no-feature-limit",
    "--no-tiny-polygon-reduction",
    "--detect-shared-borders",
)

# ---------------------------------------------------------------------------
# 5. The featured barangays and their walk-sheds
# ---------------------------------------------------------------------------
net = Network()
features = []
for pcode, place in BARANGAYS.items():
    d = w[w.study.eq(place["name"])]
    cx, cy = np.average(xy(d.lon, d.lat), axis=0, weights=d.people)
    centre = net.tree.query([cx, cy])[1]
    reach = net.within(np.array([centre]), metres(max(CHECK_WALKSHED_MIN)))[0]
    for m in sorted(CHECK_WALKSHED_MIN, reverse=True):
        ok = (reach[net.u] <= metres(m)) & (reach[net.v] <= metres(m))
        segs = shapely.linestrings(np.stack([net.xy[net.u[ok]], net.xy[net.v[ok]]], axis=1))
        shed = shapely.union_all(shapely.buffer(segs, 25)).simplify(10)
        features.append({"name": place["name"], "kind": f"walk-shed {m} min", "geometry": shed})
    features.append(
        {"name": place["name"], "kind": "barangay", "geometry": geo.set_index("pcode").to_crs(UTM).geometry[pcode]}
    )
study = gpd.GeoDataFrame(features, crs=UTM).to_crs(4326)
study["geometry"] = study.geometry.set_precision(1e-6)
(MAP_DATA / "study.geojson").write_text(study.to_json(drop_id=True) + "\n")

# ---------------------------------------------------------------------------
# 6. The page's settings: the example picks, Metro Manila's averages and bounds
# ---------------------------------------------------------------------------
m = pd.read_csv(TABLES / "measures.csv", keep_default_na=False)
mm = m[m.area.eq("Metro Manila")]


def metro(measure, stat, category=""):
    return float(mm[(mm.measure == measure) & (mm.stat == stat) & (mm.category == category)].value.iloc[0])


summary = {
    "featured": {"label": "Try an example", "pcodes": list(BARANGAYS)},
    "area": {"name": "Metro Manila", "bounds": [round(v, 4) for v in geo.total_bounds]},
    "metro": {
        "s": round(metro("M4", "mean_categories_within_15min") / len(CATEGORIES) * 100, 1),
        "m4": round(metro("M4", "mean_categories_within_15min"), 2),
        "min": {CODES[c]: round(metro("M1", "median_min", c), 1) for c in CATEGORIES},
        "w10": {CODES[c]: round(metro("M1", "share_within_10min", c) * 100) for c in CATEGORIES},
        "t": [
            round(metro("M5", s_) * 100)
            for s_ in ("share_within_500m_bus_jeepney", "share_within_1km_rail", "share_convenient")
        ],
        "pop": round(float(mm[mm.measure == "people"].value.iloc[0])),
        "a": round(float(b.area_km2.sum()), 1),
        "r": {CODES[c]: [round(metro("M1", s_, c), 1) for s_ in ("p10_min", "p90_min")] for c in CATEGORIES},
        "k": {CODES[c]: [int(metro("M2", f"median_within_{m}min", c)) for m in (5, 10, 15)] for c in CATEGORIES},
        "a9": round(metro("M4", "share_with_9") * 100),
        "jb": {
            "min": round(float(jb_metro.min_jollibee), 1),
            "w10": round(float(jb_metro.within10_jollibee) * 100),
            "k": [int(jb_metro[f"n{m}_jollibee"]) for m in (5, 10, 15)],
        },
    },
    "jollibee_stores": {"metro_manila": int(jb.pcode.notna().sum()), "with_fringe": len(jb)},
    "barangays_ranked": int(bt.score_rank.max()),
    "min_buildings": MIN_BUILDINGS,
    "hexagons_left_off": {"hexagons": len(left_off), "people": round(float(left_off.people.sum()))},
}
(MAP_DATA / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
for k, v in sizes.items():
    print(f"{k}: {v / 1e6:.1f} MB")
print(
    f"wrote {MAP_DATA.relative_to(ROOT)}/: barangays.json, barangay_measures.csv, study.geojson, "
    "jollibee.geojson, summary.json"
)
