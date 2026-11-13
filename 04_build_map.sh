#!/usr/bin/env bash
# Phase 4: the comparison site's map data in docs/map/data/ (PMTiles built with tippecanoe, and the
# per-barangay results the page compares), and its colours in docs/map/palette.js, written from
# src/shared/map_layers.py. The site (docs/index.html, a full-screen map that reads docs/map/) is a
# static file served by GitHub Pages.
# Preview:  .venv/bin/python src/04_build_map/serve_map.py   then open http://localhost:8000/
source "$(dirname "$0")/src/shared/setup.sh"

require_tippecanoe
require_inputs ./02_build_tables.sh data/derived/barangays.csv data/work/services.parquet \
  data/work/transit_routes.parquet data/work/walk_nodes.parquet data/work/walk_edges.parquet \
  data/work/jollibee.parquet
require_inputs ./03_analyse.sh data/work/walk_times.parquet data/work/jollibee_times.parquet results/tables/measures.csv

run_python src/04_build_map/build_map_tiles.py
run_python src/04_build_map/write_web_palette.py
