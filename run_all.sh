#!/usr/bin/env bash
# Every phase in order, from a clean clone to the tables, results and web map:
#   ./run_all.sh              reuse files already in data/raw/
#   ./run_all.sh --refresh    download everything again (new OpenStreetMap and Overture snapshots)
# Each phase also runs on its own, from the outputs of the one before:
#   ./01_collect_data.sh   downloads into data/raw/
#   ./02_build_tables.sh   people, services and the walking network in data/work/ and data/derived/
#   ./03_analyse.sh        walking times, the five measures and the checks in results/
#   ./04_build_map.sh      web map tiles in docs/map/data/
# Needs Python 3.12, curl and tippecanoe (brew install tippecanoe), plus the PSA 2024 census
# workbook saved by hand into data/manual/
# (docs/data-quality.md). Phases 3 and 4 are stubs until PR 3 and PR 4 and stop there.
set -euo pipefail
cd "$(dirname "$0")"
source src/shared/setup.sh
require_tippecanoe  # checked up front so a long run does not stop at the last phase

./01_collect_data.sh "$@"
./02_build_tables.sh
./03_analyse.sh
./04_build_map.sh
