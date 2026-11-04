#!/usr/bin/env bash
# Phase 3: the data analysis. From PR 3 this runs narrative notebooks in notebooks/, which
# import their logic from src/03_analyse/:
#   walk_times      nearest service and counts within 5 to 20 minutes, per origin
#   measures        M1 nearest walk, M2 choice, M3 E2SFCA, M4 15-minute coverage, M5 SDG 11.2.1
#   sensitivity     the ten checks in docs/paper.md (section 4.5)
#   audits          service, registry and street-imagery audits, with the sari-sari count
#   charts          the figures in results/figures/
# Writes results/tables/ and results/figures/ (committed).
# Stub until PR 3.
source "$(dirname "$0")/src/shared/setup.sh"

require_inputs ./02_build_tables.sh data/work data/derived

for step in walk_times measures sensitivity audits charts; do
  run_python src/03_analyse/$step.py
done
