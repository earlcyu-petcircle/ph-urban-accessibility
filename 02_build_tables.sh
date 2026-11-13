#!/usr/bin/env bash
# Phase 2: build the analysis inputs from data/raw/ and the hand downloads in data/manual/.
# Writes people (one row per residential building), the nine-category service layer, the
# Jollibee stores (a service shown beside the nine, not in the score) and the walking network to data/work/
# (gitignored), and the small barangay, Jollibee and data-quality tables to data/derived/
# (committed). About 2 minutes.
source "$(dirname "$0")/src/shared/setup.sh"

require_inputs ./01_collect_data.sh data/raw/phl_admin_boundaries.gdb.zip data/raw/phl_pop_2024_100m.tif \
  data/raw/ghs_pop_e2025_100m_r8_c30.zip data/raw/philippines-latest.osm.pbf \
  data/raw/deped_schools_osmapaaralan_2019.tsv data/raw/hotosm_education_facilities.parquet \
  data/raw/overture_places.parquet data/raw/overture_buildings.parquet
require_inputs "the hand download in docs/data-quality.md (Getting the hand downloads)" \
  data/manual/popcen2024/ncr.xlsx

for step in read_census_2024 place_people build_services build_jollibee build_walk_network build_tables; do
  run_python src/02_build_tables/$step.py
done
