#!/usr/bin/env bash
# Phase 3: the data analysis. First src/03_analyse/walk_times.py walks every resident to every
# service category along the network (data/work/walk_times.parquet), then six narrative
# notebooks in notebooks/ are executed in order:
#   01_proximity_and_choice   M1 nearest walk and M2 choice (RQ1, RQ2)
#   02_crowding               M3 crowding-adjusted supply, E2SFCA (RQ3)
#   03_coverage_and_transit   M4 15-minute coverage and M5 transit, SDG 11.2.1 (RQ4)
#   04_context_and_fairness   metro percentiles, neighbours and inequality inside each barangay (RQ5)
#   05_robustness             the ten sensitivity checks and which differences survive them
#   06_audits                 the DepEd registry match and the service and walk audit worksheets
# The notebooks import their logic from src/03_analyse/ (measures, sensitivity, audits, charts)
# and are saved with their outputs by src/shared/run_notebook.py.
# Writes results/tables/ and results/figures/ (committed). About 3 minutes.
source "$(dirname "$0")/src/shared/setup.sh"

require_inputs ./02_build_tables.sh data/derived/barangays.csv data/derived/service_quality.csv \
  data/work/origins.parquet data/work/services.parquet data/work/open_space_access.parquet \
  data/work/transit_routes.parquet data/work/walk_nodes.parquet data/work/walk_edges.parquet

run_python src/03_analyse/walk_times.py
for nb in 01_proximity_and_choice 02_crowding 03_coverage_and_transit 04_context_and_fairness 05_robustness 06_audits; do
  echo "== notebooks/$nb.ipynb"
  .venv/bin/python src/shared/run_notebook.py "notebooks/$nb.ipynb"
done
