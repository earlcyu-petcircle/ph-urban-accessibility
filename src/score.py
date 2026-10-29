#!/usr/bin/env python3
"""
Step 5: score every barangay and answer the questions.

Runs sql/resident_scores.sql and sql/barangay_scores.sql, then each question file
sql/q*.sql, and writes the results to data/derived/:
  barangay_scores.csv / .geojson   one row per barangay (the map's data)
  places_lived.geojson             outlines of the three places lived
  q1_best_worst.csv ... q6_coverage.csv
  headline.json                    metro-wide numbers the README quotes
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from common import (DERIVED, MIN_CONFIDENCE, OVERTURE_RELEASE, PLACES_LIVED, RAW, SERVICES, SQL,
                    THRESHOLDS_M, WORK, connect, run_sql)

con = connect()
con.sql(f"CREATE TABLE barangays AS SELECT * EXCLUDE (geometry) FROM '{WORK}/barangays.parquet'")
run_sql(con, "resident_scores")
run_sql(con, "barangay_scores")

for q in sorted(SQL.glob("q*.sql")):
    df = run_sql(con, q.stem).df()
    df.to_csv(DERIVED / f"{q.stem}.csv", index=False)
    print(f"wrote data/derived/{q.stem}.csv  ({len(df)} rows)")

# ---- barangay table and map layer ----
scores = con.sql("SELECT * FROM barangay_scores ORDER BY pcode").df()
scores.round(4).to_csv(DERIVED / "barangay_scores.csv", index=False)

geo = gpd.read_parquet(WORK / "barangays.parquet")[["pcode", "geometry"]].to_crs("EPSG:32651")
# Simplify all polygons together so neighbours keep their shared edges (about 8 m tolerance).
geo["geometry"] = shapely.coverage_simplify(geo.geometry.values, tolerance=8)
geo = geo.to_crs("EPSG:4326")
keep = ["pcode", "barangay", "city", "district", "pop2020", "area_km2", "density_km2", "place_lived",
        "composite"] + [f"score_{s}" for s in SERVICES] + [
        f"{s}_{m}" for s in SERVICES + ["palengke", "rail"] for m in ("share5", "share10", "median_m")]
layer = geo.merge(scores[keep], on="pcode")
for c in layer.columns:
    if c.endswith(("share5", "share10")):
        layer[c] = (layer[c] * 100).round(0)          # percent of residents
    elif c.startswith(("score_", "composite", "density", "area")) or c.endswith("median_m"):
        layer[c] = layer[c].round(1 if c in ("composite", "area_km2") else 0)
layer.to_file(DERIVED / "barangay_scores.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)
print(f"wrote data/derived/barangay_scores.csv / .geojson  ({len(layer)} barangays)")

lived = layer.dropna(subset=["place_lived"]).dissolve("place_lived", aggfunc={"pop2020": "sum"}).reset_index()
lived = lived.set_index("place_lived").loc[list(PLACES_LIVED)].reset_index()  # in the order lived
lived["label"] = lived.place_lived.map(lambda k: PLACES_LIVED[k]["label"])
lived["years"] = lived.place_lived.map(lambda k: PLACES_LIVED[k]["years"])
lived["note"] = lived.place_lived.map(lambda k: PLACES_LIVED[k]["note"])
lived.to_file(DERIVED / "places_lived.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)

# ---- headline numbers ----
r = con.sql("SELECT * FROM residents").df()
pop = r["pop"].sum()
share = {s: {m: round(float(r.loc[r[f"d_{s}"] <= t, "pop"].sum() / pop), 4) for m, t in THRESHOLDS_M.items()}
         for s in SERVICES + ["palengke", "rail"]}
osm = con.sql(f"""SELECT kind, count(*) AS n, count(DISTINCT name) AS names
                  FROM '{WORK}/osm_services.parquet' WHERE service = 'transit' GROUP BY kind""").df()
jeepney_routes = con.sql(f"""SELECT count(*) FROM '{WORK}/osm_routes.parquet'
    WHERE (tags['route'] = 'share_taxi' OR tags['bus'] = 'share_taxi'
           OR regexp_matches(coalesce(tags['network'], '') || ' ' || coalesce(tags['name'], ''), 'PUJ|[Jj]eep'))
      AND regexp_matches(coalesce(tags['network'], ''), 'National Capital|Metro Manila')""").fetchall()[0][0]
edges = con.sql(f"SELECT count(*), sum(length_m) / 1000 FROM '{WORK}/walk_edges.parquet'").fetchall()[0]
parks = con.sql(f"SELECT count(*), sum(area_m2) / 1e4 FROM '{WORK}/overture_parks.parquet'").fetchall()[0]
bscore = scores.dropna(subset=["composite"])
headline = {
    "overture_release": OVERTURE_RELEASE,
    "osm_snapshot": (RAW / "osm_snapshot.txt").read_text().strip(),
    "min_overture_confidence": MIN_CONFIDENCE,
    "people": int(round(pop)),
    "barangays": int(len(scores)),
    "barangays_with_people": int(len(bscore)),
    "origins": int(len(r)),
    "resident_weighted_composite": round(float((r["pop"] * r["s_composite"]).sum() / pop), 1),
    "resident_weighted_scores": {s: round(float((r["pop"] * r[f"s_{s}"]).sum() / pop), 1) for s in SERVICES},
    "share_within": share,
    "barangays_scoring_100": int((bscore.composite >= 99.95).sum()),
    "barangays_below_50": int((bscore.composite < 50).sum()),
    "people_in_barangays_below_50": int(bscore.loc[bscore.composite < 50, "pop2020"].sum()),
    "walk_network_segments": int(edges[0]),
    "walk_network_km": round(float(edges[1])),
    "parks_polygons": int(parks[0]),
    "parks_hectares": round(float(parks[1])),
    "transit_osm": {k: int(v) for k, v in zip(osm.kind, osm.n)},
    "rail_station_names": int(osm.loc[osm.kind == "rail", "names"].sum()),
    "jeepney_route_relations_ncr": int(jeepney_routes),
}
(DERIVED / "headline.json").write_text(json.dumps(headline, indent=2) + "\n")
print(json.dumps({k: headline[k] for k in ("people", "resident_weighted_composite", "resident_weighted_scores")}))
