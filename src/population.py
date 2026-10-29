#!/usr/bin/env python3
"""
Step 3: where people live. Writes data/work/origins.parquet, one row per lived-in
building with its share of its barangay's 2020 census population.

Python only looks up the WorldPop 100 m cell under each building centroid; the
allocation itself is sql/place_people.sql.
"""
import numpy as np
import pandas as pd
import rasterio

from common import RAW, WORK, connect, run_sql

con = connect()
bld = con.sql(f"SELECT id, subtype, area_m2, lon, lat FROM '{WORK}/overture_buildings.parquet'").df()

with rasterio.open(RAW / "phl_worldpop_2020_cn_100m.tif") as src:
    rows, cols = rasterio.transform.rowcol(src.transform, bld.lon.values, bld.lat.values)
    rows, cols = np.asarray(rows), np.asarray(cols)
    r0, c0 = rows.min(), cols.min()
    window = rasterio.windows.Window(c0, r0, cols.max() - c0 + 1, rows.max() - r0 + 1)
    grid = src.read(1, window=window, masked=True).filled(0)
bld["cell"] = rows.astype(np.int64) * 1_000_000 + cols
bld["wp_cell"] = np.clip(grid[rows - r0, cols - c0], 0, None).astype(float)

con.register("buildings", bld)
con.sql(f"""CREATE TABLE barangays AS
            SELECT pcode, pop2020, geometry AS geom FROM '{WORK}/barangays.parquet'""")
run_sql(con, "place_people")

o = pd.read_parquet(WORK / "origins.parquet")
total = con.sql("SELECT sum(pop2020) FROM barangays").fetchall()[0][0]
print(f"wrote data/work/origins.parquet  |  {len(o):,} origins carrying {o['pop'].sum():,.0f} of {total:,} people")
print(o.groupby("method").agg(origins=("pop", "size"), people=("pop", "sum"),
                              barangays=("pcode", "nunique")).round(0).to_string())
