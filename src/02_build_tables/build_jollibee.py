#!/usr/bin/env python3
"""
Build the Jollibee layer: every Jollibee store in OpenStreetMap inside Metro Manila and its
FRINGE_KM fringe, one point per store.

Jollibee is a service the site lists beside the nine (NOT_IN_SCORE in src/shared/common.py),
not one of CATEGORIES, so the nine-service measures, the 15-minute score and its rank never see
it. The site shows it like the others: in the service choice on the map and in the picks
table's service rows, marked "not in score".

The rule (is_jollibee in src/shared/service_rules.py): an `amenity=fast_food` or `restaurant`
node or area with `brand:wikidata=Q37614`, or, when no brand ID is set, a Jollibee name. Points
within DEDUPE_M of each other are one store (a few are mapped as both a node and an outline),
placed at the node where there is one, since a node sits on the shop rather than the building's
centre. Jollibee's own store locator is not used: its terms bar reuse
(docs/data-quality.md, "The Jollibee layer").

  data/work/jollibee.parquet    one row per store: store_id, name, lon, lat, pcode (Metro Manila
                                barangay, empty in the fringe), osm_ids
  data/derived/jollibee.json    the extract's snapshot time, the rule and the counts

Run after build_services.py:  python src/02_build_tables/build_jollibee.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmium
import pandas as pd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import (
    DEDUPE_M,
    DERIVED,
    FRINGE_KM,
    OSM_PBF,
    ROOT,
    STUDY_BOX,
    UTM,
    WORK,
    read_ncr_barangays,
    require,
    write_json,
)
from service_rules import JOLLIBEE_AMENITY, JOLLIBEE_NAME, JOLLIBEE_WIKIDATA, group_within, is_jollibee

require(OSM_PBF, how="Run ./01_collect_data.sh first.")
W, S, E, N = STUDY_BOX
stamp = osmium.io.Reader(str(OSM_PBF), osmium.osm.NOTHING).header().get("osmosis_replication_timestamp")

# Every restaurant node and area in the study box (areas at their centroid)
rows = []
wkb = osmium.geom.WKBFactory()
fp = osmium.FileProcessor(str(OSM_PBF)).with_areas(osmium.filter.KeyFilter("amenity"))
for obj in fp.with_filter(osmium.filter.TagFilter(*(("amenity", a) for a in JOLLIBEE_AMENITY))):
    t = obj.tags
    if obj.is_node():
        osm_id, lon, lat = f"n{obj.id}", obj.location.lon, obj.location.lat
    elif obj.is_area():
        try:
            c = shapely.from_wkb(wkb.create_multipolygon(obj)).centroid
        except RuntimeError:
            continue  # a broken multipolygon
        osm_id, lon, lat = f"{'w' if obj.from_way() else 'r'}{obj.orig_id()}", c.x, c.y
    else:
        continue
    if W <= lon <= E and S <= lat <= N:
        rows.append((osm_id, lon, lat, t.get("amenity"), t.get("brand:wikidata"), t.get("name")))
pts = pd.DataFrame(rows, columns=["osm_id", "lon", "lat", "amenity", "brand_wikidata", "name"])
jb = pts[is_jollibee(pts.amenity, pts.brand_wikidata, pts.name)].reset_index(drop=True)

# Inside Metro Manila and its fringe, one point per store
geo = read_ncr_barangays(columns=["adm4_pcode"]).to_crs(UTM)
xy = gpd.GeoSeries(gpd.points_from_xy(jb.lon, jb.lat), crs=4326).to_crs(UTM)
jb["x"], jb["y"] = xy.x.values, xy.y.values
jb = jb[shapely.contains_xy(geo.union_all().buffer(FRINGE_KM * 1000), jb.x, jb.y)].reset_index(drop=True)
jb["store"] = group_within(jb.x.values, jb.y.values, DEDUPE_M)
jb["is_node"] = jb.osm_id.str.startswith("n")
first = jb.sort_values(["store", "is_node", "osm_id"], ascending=[True, False, True]).drop_duplicates("store")
stores = first.set_index("store")[["name", "lon", "lat", "x", "y"]]
stores["osm_ids"] = jb.groupby("store").osm_id.agg(lambda s: ";".join(sorted(s)))
hit = gpd.sjoin(
    gpd.GeoDataFrame(geometry=gpd.points_from_xy(stores.x, stores.y), crs=UTM, index=stores.index),
    geo[["adm4_pcode", "geometry"]],
    predicate="intersects",
)
stores["pcode"] = hit[~hit.index.duplicated()].adm4_pcode.reindex(stores.index)
stores = stores.sort_values(["lat", "lon"]).reset_index(drop=True)
stores.insert(0, "store_id", np.arange(len(stores)))
stores[["store_id", "name", "lon", "lat", "pcode", "osm_ids"]].to_parquet(WORK / "jollibee.parquet", index=False)
print(f"wrote {(WORK / 'jollibee.parquet').relative_to(ROOT)}")

in_ncr = stores.pcode.notna()
summary = {
    "source": "OpenStreetMap, Geofabrik Philippines extract",
    "osm_snapshot": stamp,
    "rule": (
        f"amenity in {list(JOLLIBEE_AMENITY)} and (brand:wikidata = {JOLLIBEE_WIKIDATA}, "
        f"or no brand:wikidata and a name matching /{JOLLIBEE_NAME}/i); points within {DEDUPE_M} m are one store"
    ),
    "records_in_metro_manila_and_fringe": len(jb),
    "records_with_brand_id": int(jb.brand_wikidata.eq(JOLLIBEE_WIKIDATA).sum()),
    "stores_in_metro_manila_and_fringe": len(stores),
    "stores_in_metro_manila": int(in_ncr.sum()),
}
write_json(DERIVED / "jollibee.json", summary)
print(f"Jollibee: {summary['stores_in_metro_manila']} stores in Metro Manila, {len(stores)} with the fringe")
