#!/usr/bin/env bash
# Phase 4: the web map's vector tiles in docs/map/data/ (PMTiles, built with tippecanoe).
# Home locations are never written to the map.
# Preview:  .venv/bin/python src/04_build_map/serve_map.py   then open http://localhost:8000/map/
# Stub until PR 4.
source "$(dirname "$0")/src/shared/setup.sh"

require_tippecanoe
require_inputs ./03_analyse.sh results/tables

run_python src/04_build_map/build_map_tiles.py
