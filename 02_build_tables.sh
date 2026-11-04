#!/usr/bin/env bash
# Phase 2: build the analysis inputs from data/raw/ and the hand downloads in data/manual/.
# Writes people (one row per residential building), the nine-category service layer and the
# walking network to data/work/ (gitignored), and the small barangay and data-quality tables
# to data/derived/ (committed).
# Stub until PR 2.
source "$(dirname "$0")/src/shared/setup.sh"

require_inputs ./01_collect_data.sh data/raw
require_inputs "the hand downloads in docs/paper.md (section 3)" data/manual

for step in read_census_2024 place_people build_services build_walk_network build_tables; do
  run_python src/02_build_tables/$step.py
done
