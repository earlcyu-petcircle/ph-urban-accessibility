#!/usr/bin/env python3
"""
Download Overture Maps places and buildings inside the study box (Metro Manila plus the 2 km
fringe; STUDY_BOX in src/shared/common.py) for release OVERTURE_RELEASE.

Reads the public GeoParquet release on S3 directly with DuckDB, filtering on each feature's
bbox so only matching row groups are read (no account, no API key), and keeps slim columns:

  data/raw/overture_places.parquet      every place: name, categories, confidence, operating
                                        status, source datasets and its point
  data/raw/overture_buildings.parquet   every footprint: subtype, class, floors, height,
                                        footprint area in m2, centroid and source dataset

Files that already exist are kept; pass --refresh to download them again.
Run after download_sources.sh:  python src/01_collect_data/download_overture.py
"""

import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import OVERTURE_BUILDINGS, OVERTURE_PLACES, OVERTURE_RELEASE, ROOT, STUDY_BOX, UTM

S3 = f"s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}"
W, S, E, N = STUDY_BOX
IN_BOX = f"bbox.xmin <= {E} AND bbox.xmax >= {W} AND bbox.ymin <= {N} AND bbox.ymax >= {S}"

QUERIES = {
    OVERTURE_PLACES: f"""
        SELECT id, names."primary" AS name, basic_category, taxonomy."primary" AS category,
               taxonomy.hierarchy AS hierarchy, taxonomy.alternates AS alt_categories,
               confidence, operating_status,
               list_transform(sources, lambda s: s.dataset) AS datasets,
               ST_X(geometry) AS lon, ST_Y(geometry) AS lat
        FROM read_parquet('{S3}/theme=places/type=place/*', hive_partitioning = 1)
        WHERE {IN_BOX}
    """,
    OVERTURE_BUILDINGS: f"""
        SELECT id, subtype, class, num_floors, height, is_underground,
               sources[1].dataset AS dataset,
               ST_Area(ST_Transform(geometry, 'EPSG:4326', '{UTM}', always_xy := true)) AS area_m2,
               ST_X(ST_Centroid(geometry)) AS lon, ST_Y(ST_Centroid(geometry)) AS lat
        FROM read_parquet('{S3}/theme=buildings/type=building/*', hive_partitioning = 1)
        WHERE {IN_BOX}
    """,
}

refresh = "--refresh" in sys.argv[1:]
con = duckdb.connect()
for ext in ("httpfs", "spatial"):
    con.install_extension(ext)
    con.load_extension(ext)
con.execute("SET s3_region = 'us-west-2'")
con.execute("SET enable_progress_bar = false")

for out, query in QUERIES.items():
    rel = out.relative_to(ROOT)
    if out.exists() and not refresh:
        print(f"keep     {rel}")
        continue
    t = time.time()
    part = out.with_suffix(".parquet.part")
    con.execute(f"COPY ({query}) TO '{part}' (FORMAT parquet)")
    part.rename(out)
    n = con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    print(f"download {rel}: {n:,} rows from Overture {OVERTURE_RELEASE} ({time.time() - t:.0f}s)")
