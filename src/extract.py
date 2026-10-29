#!/usr/bin/env python3
"""
Step 1: pull every input the analysis needs into data/work/ as Parquet.

Overture places, buildings and parks are read straight from Overture's public S3
bucket (release in common.OVERTURE_RELEASE), filtered to the study box by DuckDB.
OpenStreetMap is read from the Geofabrik extract with ST_ReadOSM.
Outputs that already exist are kept; pass --refresh to rebuild them.
"""
import sys
import time

from common import WORK, connect, run_sql

STEPS = [  # (sql file, output it writes)
    ("extract_overture_places", "overture_places.parquet"),
    ("extract_overture_buildings", "overture_buildings.parquet"),
    ("extract_overture_parks", "overture_parks.parquet"),
    ("extract_osm", "osm_routes.parquet"),
    ("walk_network", "walk_edges.parquet"),
    ("osm_services", "osm_services.parquet"),
]

refresh = "--refresh" in sys.argv
con = connect()
for name, out in STEPS:
    if (WORK / out).exists() and not refresh:
        print(f"keep     data/work/{out}")
        continue
    t = time.time()
    run_sql(con, name)
    print(f"wrote    data/work/{out}  ({time.time() - t:.0f}s, sql/{name}.sql)")
