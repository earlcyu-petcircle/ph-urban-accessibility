#!/usr/bin/env python3
"""
Build the nine-category service layer (CATEGORIES in src/shared/common.py) from Overture
places, OpenStreetMap and the DepEd public-school registry, and check it against that registry
and Healthsites.io.

Sources and rules (docs/data-quality.md, "The service layer", explains each one):
  - Overture places at confidence 0.3 or more (the lowest value of check 08), not marked
    closed, sorted into categories by their taxonomy and, for health and markets, their name;
  - OpenStreetMap shops, amenities, healthcare, open-space polygons, stops and stations from
    the Geofabrik extract, sorted by their tags;
  - the DepEd school list (OSMaPaaralan, 2019): every public school with its level and enrolment.
Inside each category, points within DEDUPE_M of each other that share a name (or where one
has none) are one service: they share a `dup_group`, and `in_default` marks one per group from
the default layer (OpenStreetMap, DepEd and Overture at confidence 0.5 or more). Services count
inside Metro Manila and its FRINGE_KM fringe.

Sari-sari stores are almost absent from both sources; the few mapped ones stay in food retail
as kind `sari_sari` (the README's Limitations section).

  data/work/services.parquet             one row per source record: category, kind, source,
                                         name, point, confidence, level, capacity, dup_group
  data/work/open_space_access.parquet    points every OPEN_SPACE_ACCESS_SPACING_M round each
                                         open space, where a walk reaches it
  data/work/transit_routes.parquet       vertices of every bus and jeepney route in the box
  data/derived/service_quality.csv       counts by source and registry match rates by area
  data/work/services_stats.json          extraction counts, gathered by build_tables.py

Run after place_people.py:  python src/02_build_tables/build_services.py
"""

import re
import sys
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import osmium
import pandas as pd
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import (
    BARANGAYS,
    CAMPUS_CATEGORIES,
    CAMPUS_DEDUPE_M,
    CATEGORIES,
    DEDUPE_M,
    DEPED_SCHOOLS,
    DERIVED,
    FRINGE_KM,
    HEALTHSITES_CSV,
    HOT_EDUCATION,
    OPEN_SPACE_ACCESS_SPACING_M,
    OPEN_SPACE_MIN_HA,
    OSM_PBF,
    OVERTURE_CONFIDENCE_SENSITIVITY,
    OVERTURE_MIN_CONFIDENCE,
    OVERTURE_PLACES,
    ROOT,
    STUDY_BOX,
    UTM,
    WORK,
    read_ncr_barangays,
    require,
    write_json,
)
from service_rules import (
    FOOD_SHOPS,
    MARKET_NAME,
    NOT_MARKET,
    OPEN_SPACE,
    PRIVATE_SCHOOL,
    SARI_SARI,
    SCHOOL_PART,
    SUPERMARKET,
    has,
    health_category,
    norm_name,
    same_place,
    school_level,
    school_rows,
)

require(OVERTURE_PLACES, OSM_PBF, DEPED_SCHOOLS, HOT_EDUCATION, how="Run ./01_collect_data.sh first.")

W, S, E, N = STUDY_BOX

# ---------------------------------------------------------------------------
# 1. Overture places
# ---------------------------------------------------------------------------
con = duckdb.connect()
ov = con.sql(f"""
    SELECT id AS source_id, name, category, basic_category, confidence, operating_status, lon, lat,
           array_to_string(datasets, ';') AS datasets
    FROM read_parquet('{OVERTURE_PLACES}')
    WHERE confidence >= {min(OVERTURE_CONFIDENCE_SENSITIVITY)}
      AND coalesce(operating_status, 'open') = 'open'
      AND lon BETWEEN {W} AND {E} AND lat BETWEEN {S} AND {N}
""").df()
cat, name = ov.category.fillna(""), ov.name
ov_rows = []
# Food retail
food = cat.isin(
    [
        "grocery_store",
        "supermarket",
        "convenience_store",
        "organic_grocery_store",
        "korean_grocery_store",
        "asian_grocery_store",
        "international_grocery_store",
        "japanese_grocery_store",
        "chinese_grocery_store",
        "indian_grocery_store",
    ]
) | has(name, SARI_SARI)
food &= ~has(name, MARKET_NAME) | has(name, NOT_MARKET)
kind = np.select(
    [has(name, SARI_SARI), cat.eq("convenience_store"), has(name, SUPERMARKET)],
    ["sari_sari", "convenience", "supermarket"],
    "grocery",
)
ov_rows.append(ov[food].assign(category="food_retail", kind=kind[food.values]))
# Palengke: farmers' markets, and market names on food and shopping places
shopish = cat.isin(
    [
        "grocery_store",
        "produce_store",
        "fishmonger",
        "butcher_shop",
        "meat_shop",
        "shopping",
        "flea_market",
        "market",
        "food_and_drink",
        "seafood_market",
        "fruits_and_vegetables",
        "",
    ]
)
palengke = (cat.eq("farmers_market") | (shopish & has(name, MARKET_NAME))) & ~has(name, NOT_MARKET)
ov_rows.append(ov[palengke].assign(category="palengke", kind="market"))
# Pharmacy
pharmacy = cat.isin(["pharmacy", "drugstore"]) | ov.basic_category.eq("pharmacy_and_drug_store")
ov_rows.append(ov[pharmacy].assign(category="pharmacy", kind="pharmacy"))
# Health: Overture's hospital category holds many clinics, so names decide
hospital_tag = cat.isin(["hospital", "emergency_department", "medical_center", "childrens_hospital"])
primary_tag = cat.isin(
    [
        "health_care",
        "family_practice",
        "outpatient_care_facility",
        "pediatric_clinic",
        "maternity_center",
        "primary_care_or_general_clinic",
        "community_health_center",
        "health_department",
        "urgent_care_clinic",
        "medical_service_organization",
        "internal_medicine",
        "doctors_office",
    ]
)
health = pd.Series(health_category(name, hospital_tag, primary_tag, False), index=ov.index)
ov_rows.append(ov[health.notna()].assign(category=health[health.notna()], kind="facility"))
# Public schools: Overture's public_school category, or a public-school name
school_cat = cat.isin(["school", "public_school", "elementary_school", "high_school", "middle_school"])
public = school_cat & (cat.eq("public_school") | has(name, r"\bdeped\b") | ~has(name, PRIVATE_SCHOOL))
public &= ~has(name, SCHOOL_PART)
pub = ov[public]
ov_rows.append(school_rows(pub, school_level(pub.name)).assign(kind="school"))
# Transit: bus terminals (Overture has no jeepney routes and few stops; rail comes from OpenStreetMap)
bus_term = cat.eq("bus_station")
ov_rows.append(ov[bus_term].assign(category="transit", kind="bus_terminal"))
ov_places = pd.concat(ov_rows, ignore_index=True).assign(source="overture")
print(
    f"Overture: {len(ov):,} places at confidence >= {min(OVERTURE_CONFIDENCE_SENSITIVITY)} in the box, "
    f"{len(ov_places):,} service records"
)


# ---------------------------------------------------------------------------
# 2. OpenStreetMap: points, open space, stops, stations and route vertices
# ---------------------------------------------------------------------------
def in_box(lon, lat):
    return W <= lon <= E and S <= lat <= N


ROUTE_MODES = {"bus", "share_taxi", "minibus", "jeepney", "light_rail", "subway", "train", "monorail"}
routes, route_ways, rail_stops = {}, {}, set()
for r in osmium.FileProcessor(str(OSM_PBF), osmium.osm.RELATION).with_filter(
    osmium.filter.TagFilter(("type", "route"))
):
    t = r.tags
    mode = (t.get("route") or "").lower()
    if mode not in ROUTE_MODES:
        continue
    network, rname = t.get("network", ""), t.get("name", "")
    label = f"{network} {rname} {t.get('operator', '')}"
    if mode in ("share_taxi", "jeepney") or re.search(r"\bPUJ\b|jeep", label, re.I):
        kind = "jeepney"
    elif mode in ("bus", "minibus"):
        kind = "bus"
    elif network in ("Manila LRT", "Manila MRT") or re.search(r"\b(LRT|MRT)\b", label):
        kind = "rail"
    else:
        continue  # PNR is suspended in Metro Manila since March 2024; the Subway is not open
    routes[r.id] = {"route_id": r.id, "mode": kind, "network": network, "name": rname, "ref": t.get("ref", "")}
    for m in r.members:
        if m.type == "w" and kind in ("bus", "jeepney") and not m.role.startswith("platform"):
            route_ways.setdefault(m.ref, []).append(r.id)
        elif m.type == "n" and kind == "rail" and (m.role.startswith("stop") or m.role.startswith("platform")):
            rail_stops.add((m.ref, r.id))
rail_stop_route = {n: rid for n, rid in rail_stops}

POI_KEYS = ("shop", "amenity", "healthcare", "leisure", "landuse", "place", "highway", "public_transport", "railway")


def poi_tags(t):
    return {
        k: t.get(k)
        for k in (
            "shop",
            "amenity",
            "healthcare",
            "leisure",
            "landuse",
            "place",
            "highway",
            "public_transport",
            "railway",
            "name",
            "access",
            "operator:type",
            "isced:level",
            "school:level",
            "bus",
            "station",
            "network",
            "disused",
            "healthcare:speciality",
        )
        if t.get(k) is not None
    }


points, spaces, vertices = [], [], []
wkb = osmium.geom.WKBFactory()
fp = (
    osmium.FileProcessor(str(OSM_PBF))
    .with_areas(osmium.filter.KeyFilter("leisure", "landuse", "place", "amenity", "healthcare", "shop"))
    .with_filter(osmium.filter.KeyFilter(*POI_KEYS))
)
for obj in fp:
    t = obj.tags
    if obj.is_node():
        loc = obj.location
        if loc.valid() and in_box(loc.lon, loc.lat):
            points.append(("n", obj.id, loc.lon, loc.lat, poi_tags(t), None))
    elif obj.is_way():
        if obj.id in route_ways:
            for n in obj.nodes:
                if n.location.valid() and in_box(n.location.lon, n.location.lat):
                    vertices.append((obj.id, n.ref, n.location.lon, n.location.lat))
    elif obj.is_area():
        tags = poi_tags(t)
        if not any(k in tags for k in ("shop", "amenity", "healthcare", "leisure", "landuse", "place")):
            continue
        try:
            geom = shapely.from_wkb(wkb.create_multipolygon(obj))
        except RuntimeError:
            continue  # a broken multipolygon
        c = geom.centroid
        if not in_box(c.x, c.y):
            continue
        osm_type = "w" if obj.from_way() else "r"
        campus = tags.get("amenity") in ("hospital", "school", "marketplace") or tags.get("healthcare") == "hospital"
        points.append((osm_type, obj.orig_id(), c.x, c.y, tags, geom if campus else None))
        if any((k, tags.get(k)) in OPEN_SPACE for k in ("leisure", "landuse", "place")):
            spaces.append((osm_type, obj.orig_id(), tags, geom))

pts = pd.DataFrame(points, columns=["osm_type", "osm_id", "lon", "lat", "tags", "footprint"])
tag = {
    k: pts.tags.map(lambda d, k=k: d.get(k))
    for k in (
        "shop",
        "amenity",
        "healthcare",
        "highway",
        "public_transport",
        "railway",
        "name",
        "operator:type",
        "isced:level",
        "school:level",
        "bus",
        "station",
        "network",
        "access",
    )
}
pts["name"] = tag["name"]
pts["source_id"] = pts.osm_type + pts.osm_id.astype(str)
osm_rows = []
# Food retail and sari-sari stores
shop = tag["shop"].fillna("")
food = shop.isin(list(FOOD_SHOPS)) | (shop.ne("") & has(pts.name, SARI_SARI))
kind = np.where(has(pts.name, SARI_SARI), "sari_sari", shop.map(FOOD_SHOPS).fillna("grocery"))
kind = np.where((kind == "grocery") & has(pts.name, SUPERMARKET), "supermarket", kind)
osm_rows.append(pts[food].assign(category="food_retail", kind=kind[food.values]))
# Palengke
amenity = tag["amenity"].fillna("")
palengke = (amenity.eq("marketplace") | shop.eq("market")) & ~has(pts.name, NOT_MARKET)
osm_rows.append(pts[palengke].assign(category="palengke", kind="market"))
# Pharmacy (Watsons and other chemists sell medicine in the Philippines)
healthcare = tag["healthcare"].fillna("")
pharmacy = amenity.eq("pharmacy") | healthcare.eq("pharmacy") | shop.eq("chemist")
osm_rows.append(pts[pharmacy].assign(category="pharmacy", kind="pharmacy"))
# Health
hospital_tag = amenity.eq("hospital") | healthcare.eq("hospital")
primary_tag = amenity.isin(["clinic", "doctors"]) | healthcare.isin(["clinic", "doctor", "centre"])
health = pd.Series(health_category(pts.name, hospital_tag, primary_tag, True), index=pts.index)
osm_rows.append(pts[health.notna()].assign(category=health[health.notna()], kind="facility"))
# Public schools: operator:type when tagged, otherwise the name
op = tag["operator:type"].fillna("")
school = amenity.eq("school") & tag["access"].fillna("").ne("private")
public = school & (op.isin(["public", "government"]) | (op.eq("") & ~has(pts.name, PRIVATE_SCHOOL)))
isced = tag["isced:level"].fillna(tag["school:level"].fillna(""))
pub = pts[public]
osm_rows.append(school_rows(pub, school_level(pub.name, isced[public])).assign(kind="school"))
# Transit stops and stations
bus_stop = tag["highway"].eq("bus_stop") | (tag["public_transport"].eq("platform") & tag["railway"].isna())
osm_rows.append(pts[bus_stop & pts.osm_type.eq("n")].assign(category="transit", kind="bus_stop"))
rail = pts[pts.osm_type.eq("n") & pts.osm_id.isin(rail_stop_route)]
rail = rail.assign(network=rail.osm_id.map(rail_stop_route).map(lambda r: routes[r]["network"]))
osm_rows.append(rail.assign(category="transit", kind="rail_station"))
osm_places = pd.concat(osm_rows, ignore_index=True).assign(source="osm", confidence=np.nan)
print(f"OpenStreetMap: {len(pts):,} tagged points and areas in the box, {len(osm_places):,} service records")

# Open space of at least OPEN_SPACE_MIN_HA, open to the public
sp = gpd.GeoDataFrame(
    {"source_id": [f"{t}{i}" for t, i, _, _ in spaces], "tags": [x for _, _, x, _ in spaces]},
    geometry=[g for *_, g in spaces],
    crs=4326,
)
sp["name"] = sp.tags.map(lambda d: d.get("name"))
sp["kind"] = sp.tags.map(lambda d: next(v for k, v in OPEN_SPACE if d.get(k) == v))
sp["access"] = sp.tags.map(lambda d: d.get("access", ""))
sp_utm = sp.to_crs(UTM)
sp["area_ha"] = sp_utm.area / 1e4
open_ = sp[(sp.area_ha >= OPEN_SPACE_MIN_HA) & ~sp.access.isin(["private", "no", "customers", "permit"])]
# A park drawn inside a bigger one (a playground in a park) is reached through the bigger one
inner = gpd.sjoin(
    open_[["source_id", "geometry"]].to_crs(UTM).assign(geometry=lambda d: d.representative_point()),
    open_[["source_id", "area_ha", "geometry"]].to_crs(UTM),
    predicate="within",
)
inner = inner[(inner.source_id_left != inner.source_id_right)]
nested = set(inner.source_id_left)
open_ = open_[~open_.source_id.isin(nested)].copy()
cent = open_.to_crs(UTM).representative_point().to_crs(4326)
osm_open = pd.DataFrame(
    {
        "source_id": open_.source_id,
        "name": open_.name,
        "kind": open_.kind,
        "area_ha": open_.area_ha,
        "lon": cent.x,
        "lat": cent.y,
        "category": "open_space",
        "source": "osm",
    }
)
edges = shapely.segmentize(shapely.boundary(open_.to_crs(UTM).geometry.values), OPEN_SPACE_ACCESS_SPACING_M)
access_pts = []
for sid, g in zip(open_.source_id, edges, strict=True):
    xy = shapely.get_coordinates(g)
    access_pts.append(pd.DataFrame({"source_id": sid, "x": xy[:, 0], "y": xy[:, 1]}))
access = pd.concat(access_pts, ignore_index=True)
lonlat = gpd.GeoSeries(gpd.points_from_xy(access.x, access.y), crs=UTM).to_crs(4326)
access = access.assign(lon=lonlat.x.values, lat=lonlat.y.values).drop(columns=["x", "y"])
print(
    f"open space: {len(sp):,} mapped, {len(open_):,} of {OPEN_SPACE_MIN_HA} ha or more and open "
    f"({len(nested)} nested ones dropped), {len(access):,} access points"
)


# ---------------------------------------------------------------------------
# 3. The DepEd public-school registry (OSMaPaaralan 2019)
# ---------------------------------------------------------------------------
dep = pd.read_csv(DEPED_SCHOOLS, sep="\t", dtype=str)
dep["lon"], dep["lat"] = pd.to_numeric(dep.longitude, errors="coerce"), pd.to_numeric(dep.latitude, errors="coerce")
dep = dep[dep.lon.between(W, E) & dep.lat.between(S, N)].copy()
dep["enrolment"] = pd.to_numeric(dep["population:pupils:2015"], errors="coerce")
dep["source_id"] = "deped" + dep["@id"]
dep_rows = school_rows(
    dep[["source_id", "name", "lon", "lat", "enrolment"]], school_level(dep.name, dep["isced:level"])
)
dep_rows = dep_rows.assign(source="deped", kind="school", capacity=dep_rows.enrolment, capacity_source="enrolment_2015")
print(f"DepEd registry: {len(dep):,} public schools in the box, {len(dep_rows):,} school-level records")


# ---------------------------------------------------------------------------
# 4. One table, limited to Metro Manila and its fringe, with duplicates grouped
# ---------------------------------------------------------------------------
cols = [
    "category",
    "kind",
    "source",
    "source_id",
    "name",
    "lon",
    "lat",
    "confidence",
    "datasets",
    "level",
    "capacity",
    "capacity_source",
    "area_ha",
    "network",
    "footprint",
]
parts = [ov_places, osm_places, osm_open, dep_rows]
svc = pd.concat([p.reindex(columns=cols) for p in parts], ignore_index=True)
svc = svc[svc.category.isin(CATEGORIES)].reset_index(drop=True)

geo = read_ncr_barangays(columns=["adm4_pcode", "adm3_name"])
ncr_utm = geo.to_crs(UTM)
fringe = ncr_utm.union_all().buffer(FRINGE_KM * 1000)
xy = gpd.GeoSeries(gpd.points_from_xy(svc.lon, svc.lat), crs=4326).to_crs(UTM)
svc["x"], svc["y"] = xy.x.values, xy.y.values
svc = svc[shapely.contains_xy(fringe, svc.x, svc.y)].reset_index(drop=True)
hit = gpd.sjoin(
    gpd.GeoDataFrame(geometry=gpd.points_from_xy(svc.x, svc.y), crs=UTM),
    ncr_utm[["adm4_pcode", "geometry"]],
    predicate="intersects",
)
hit = hit[~hit.index.duplicated()]
svc["pcode"] = hit.adm4_pcode.reindex(svc.index).values

svc["key"] = svc.name.map(norm_name)
svc["default_source"] = svc.source.isin(["osm", "deped"]) | (svc.confidence >= OVERTURE_MIN_CONFIDENCE)
svc["dup_group"] = -1
next_group = 0
for category, g in svc.groupby("category"):
    idx = g.index.values
    if category == "transit":  # rail stops share a station by name; stops and terminals stand alone
        keys = np.where(g.kind.eq("rail_station"), "rail:" + g.network.fillna("") + ":" + g.key, "id:" + g.source_id)
        codes = pd.factorize(keys)[0]
    else:
        radius = CAMPUS_DEDUPE_M if category in CAMPUS_CATEGORIES else DEDUPE_M
        tree = cKDTree(g[["x", "y"]].values)
        pairs = tree.query_pairs(radius, output_type="ndarray")
        k, xy_ = g.key.values, g[["x", "y"]].values
        a, b = pairs[:, 0], pairs[:, 1]
        near = np.hypot(*(xy_[a] - xy_[b]).T) <= DEDUPE_M
        named = (k[a] != "") & (k[b] != "")
        same = np.array([same_place(x, y) for x, y in zip(k[a], k[b], strict=True)], dtype=bool)
        keep_pair = same & (near | named)  # beyond DEDUPE_M, both must be named
        a, b = a[keep_pair], b[keep_pair]
        if category in CAMPUS_CATEGORIES:  # a point on an OpenStreetMap campus, named alike, is that campus
            fp = g.footprint.notna().values
            if fp.any():
                shapes = gpd.GeoSeries(list(g.footprint[fp]), crs=4326).to_crs(UTM).buffer(DEDUPE_M).values
                pi, si = shapely.STRtree(shapes).query(shapely.points(xy_), predicate="intersects")
                owner = np.flatnonzero(fp)[si]
                ok = (owner != pi) & np.array(
                    [same_place(k[o], k[q]) for o, q in zip(owner, pi, strict=True)], dtype=bool
                )
                a, b = np.concatenate([a, owner[ok]]), np.concatenate([b, pi[ok]])
        m = coo_matrix((np.ones(len(a)), (a, b)), shape=(len(g), len(g)))
        codes = connected_components(m, directed=False)[1]
    svc.loc[idx, "dup_group"] = codes + next_group
    next_group += codes.max() + 1
# Where a registry lists a category, it decides what belongs in it: DepEd for public schools
# (names cannot tell public from private, and misplaced Overture records pass a name rule).
# The OpenStreetMap and Overture records stay for check 07.
REGISTRY_FOR = {"public_elementary": "deped", "public_high": "deped"}
group_sources = svc.groupby("dup_group").source.agg(set)
listed = pd.Series(True, index=svc.index)
for category, registry in REGISTRY_FOR.items():
    rows_ = svc.category.eq(category)
    listed[rows_] = svc.dup_group[rows_].map(lambda g, r=registry: r in group_sources[g])
# One record per group carries it in the default layer: OpenStreetMap first (its points sit on
# the building), then the registries, then the most confident Overture record
rank = svc.source.map({"osm": 0, "deped": 1, "overture": 2})
order = svc[svc.default_source].assign(rank=rank, conf=-svc.confidence.fillna(1)).sort_values(["rank", "conf"])
svc["in_default"] = svc.index.isin(order.drop_duplicates("dup_group").index) & listed
svc["sources_in_group"] = svc.groupby("dup_group").source.transform(lambda s: ";".join(sorted(set(s))))
# Registry capacity (beds, enrolment) carries to its group
cap = svc[svc.capacity.notna()].groupby("dup_group").capacity.max()
svc["group_capacity"] = svc.dup_group.map(cap)

svc.insert(0, "service_id", np.arange(len(svc)))
out_cols = [
    "service_id",
    "category",
    "kind",
    "source",
    "source_id",
    "name",
    "lon",
    "lat",
    "pcode",
    "confidence",
    "datasets",
    "level",
    "capacity",
    "capacity_source",
    "group_capacity",
    "area_ha",
    "network",
    "dup_group",
    "sources_in_group",
    "in_default",
]
svc[out_cols].to_parquet(WORK / "services.parquet", index=False)
access = access.merge(svc.loc[svc.category.eq("open_space"), ["source_id", "service_id"]], on="source_id")
access[["service_id", "lon", "lat"]].to_parquet(WORK / "open_space_access.parquet", index=False)
rv = pd.DataFrame(vertices, columns=["way_id", "node_id", "lon", "lat"]).drop_duplicates(["way_id", "node_id"])
rv = rv.merge(
    pd.DataFrame([(w, r) for w, rs in route_ways.items() for r in rs], columns=["way_id", "route_id"]), on="way_id"
).merge(pd.DataFrame(routes.values()), on="route_id")
rv.to_parquet(WORK / "transit_routes.parquet", index=False)
for f in ("services.parquet", "open_space_access.parquet", "transit_routes.parquet"):
    print(f"wrote {(WORK / f).relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# 5. Registry matches and completeness checks
# ---------------------------------------------------------------------------
def found(reg, layer, radius):
    """For each outside point, whether a layer point of the same category is within `radius` metres."""
    hit = np.zeros(len(reg), dtype=bool)
    for category, r in reg.groupby("category"):
        lay = layer[layer.category.eq(category)]
        if len(lay):
            d, _ = cKDTree(lay[["x", "y"]].values).query(r[["x", "y"]].values)
            hit[reg.index.get_indexer(r.index)] = d <= radius
    return hit


# A registry record is found when its duplicate group holds an Overture or OpenStreetMap record
# of the default layer (the same rule that merges them)
open_layer_groups = set(svc.dup_group[svc.source.isin(["osm", "overture"]) & svc.default_source])
AREAS = {"Metro Manila": geo.adm4_pcode.values}
for city in ("City of Manila", "Quezon City", "City of Pasig"):
    AREAS[city] = geo.adm4_pcode[geo.adm3_name.eq(city)].values
for pcode, place in BARANGAYS.items():
    AREAS[place["name"]] = [pcode]

rows = []
regs = {"deped": svc[svc.source.eq("deped")]}
for reg_name, reg in regs.items():
    reg = reg.assign(found=reg.dup_group.isin(open_layer_groups))
    for area, pcodes in AREAS.items():
        for category, r in reg[reg.pcode.isin(pcodes)].groupby("category"):
            rows.append(
                {
                    "area": area,
                    "category": category,
                    "measure": f"{reg_name}_registry_found",
                    "value": int(r.found.sum()),
                    "of": len(r),
                }
            )
for area, pcodes in AREAS.items():
    in_area = svc[svc.pcode.isin(pcodes)]
    for category in CATEGORIES:
        c = in_area[in_area.category.eq(category)]
        d = c[c.in_default]
        rows += [
            {"area": area, "category": category, "measure": f"records_{s}", "value": int(c.source.eq(s).sum())}
            for s in ("overture", "osm", "deped")
        ]
        rows.append(
            {
                "area": area,
                "category": category,
                "measure": "overture_confidence_0.5",
                "value": int((c.source.eq("overture") & (c.confidence >= OVERTURE_MIN_CONFIDENCE)).sum()),
            }
        )
        rows.append({"area": area, "category": category, "measure": "services_default", "value": len(d)})
        rows.append(
            {
                "area": area,
                "category": category,
                "measure": "services_in_more_than_one_source",
                "value": int(d.sources_in_group.str.contains(";").sum()),
            }
        )
    food = in_area[in_area.category.eq("food_retail") & in_area.in_default]
    for k in ("supermarket", "grocery", "convenience", "sari_sari"):
        rows.append(
            {
                "area": area,
                "category": "food_retail",
                "measure": f"services_default_{k}",
                "value": int(food.kind.eq(k).sum()),
            }
        )
quality = pd.DataFrame(rows)
quality["of"] = quality["of"].astype("Int64")
quality.to_csv(DERIVED / "service_quality.csv", index=False)
print(f"wrote {(DERIVED / 'service_quality.csv').relative_to(ROOT)}")

# Healthsites.io (a completeness check, when the HDX download got through)
healthsites = None
if HEALTHSITES_CSV.exists():
    hs = pd.read_csv(HEALTHSITES_CSV, dtype=str)
    lon_col = next(c for c in hs.columns if c.lower() in ("x", "lon", "longitude"))
    lat_col = next(c for c in hs.columns if c.lower() in ("y", "lat", "latitude"))
    hs["lon"], hs["lat"] = pd.to_numeric(hs[lon_col], errors="coerce"), pd.to_numeric(hs[lat_col], errors="coerce")
    hs = hs[hs.lon.between(W, E) & hs.lat.between(S, N)]
    a = hs.get("amenity", pd.Series("", index=hs.index)).fillna("")
    hs["category"] = np.select(
        [a.eq("hospital"), a.isin(["clinic", "doctors"]), a.eq("pharmacy")],
        ["hospital", "primary_care", "pharmacy"],
        None,
    )
    hs = hs[hs.category.notna()].reset_index(drop=True)
    hxy = gpd.GeoSeries(gpd.points_from_xy(hs.lon, hs.lat), crs=4326).to_crs(UTM)
    hs["x"], hs["y"] = hxy.x.values, hxy.y.values
    hs = hs[shapely.contains_xy(ncr_utm.union_all(), hs.x, hs.y)]
    hs["found"] = found(hs, svc[svc.in_default], 2 * DEDUPE_M)
    healthsites = {c: {"found": int(g.found.sum()), "of": len(g)} for c, g in hs.groupby("category")}

# HOT education facilities: the same OpenStreetMap schools, as a check on this extraction
hot = pd.read_parquet(HOT_EDUCATION, columns=["amenity", "operator_type", "adm1_pcode"])
hot = hot[hot.adm1_pcode.eq("PH13") & hot.amenity.eq("school")]
osm_schools_ncr = pts[amenity.eq("school")]
osm_schools_ncr = int(shapely.contains_xy(geo.union_all(), osm_schools_ncr.lon, osm_schools_ncr.lat).sum())

stats = {
    "overture_places_in_box": len(ov),
    "overture_records_by_category": {k: int(v) for k, v in ov_places.category.value_counts().items()},
    "osm_tagged_points_and_areas_in_box": len(pts),
    "osm_records_by_category": {k: int(v) for k, v in osm_places.category.value_counts().items()},
    "osm_schools_in_metro_manila_this_extraction": osm_schools_ncr,
    "hot_education_schools_in_metro_manila": len(hot),
    "hot_education_schools_public": int(hot.operator_type.isin(["public", "government"]).sum()),
    "open_space_mapped": len(sp),
    "open_space_kept": len(open_),
    "open_space_nested_dropped": len(nested),
    "open_space_access_points": len(access),
    "routes": {k: int(v) for k, v in pd.Series([r["mode"] for r in routes.values()]).value_counts().items()},
    "route_vertices_in_box": {k: int(v) for k, v in rv.drop_duplicates("node_id").groupby("mode").size().items()},
    "routes_in_box": {k: int(v) for k, v in rv.drop_duplicates("route_id").groupby("mode").size().items()},
    "deped_schools_in_box": len(dep),
    "healthsites_check": healthsites,
    "records_in_fringe": len(svc),
    "records_by_source": {k: int(v) for k, v in svc.source.value_counts().items()},
    "default_services_by_category": {k: int(v) for k, v in svc[svc.in_default].category.value_counts().items()},
    "default_services_in_metro_manila_by_category": {
        k: int(v) for k, v in svc[svc.in_default & svc.pcode.notna()].category.value_counts().items()
    },
}
write_json(WORK / "services_stats.json", stats)
print(pd.Series(stats["default_services_in_metro_manila_by_category"]).to_string())
