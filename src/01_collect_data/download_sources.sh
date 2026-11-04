#!/usr/bin/env bash
# Download the open datasets into data/raw/ (gitignored).
# No API keys, no logins, no proprietary data. Run from the repo root.
# Files that already exist are kept; pass --refresh to download everything again
# (OpenStreetMap changes over time, so a refresh can change counts).
#
# Planned sources (docs/paper.md, section 3):
#   OCHA COD-AB Philippines barangay boundaries (HDX, CC BY-IGO)
#   WorldPop constrained 100 m population, 2024 (HDX, CC BY 4.0), and JRC GHS-POP for the check
#   Geofabrik OpenStreetMap extract for the Philippines (ODbL): services, parks, network, transit
#   Healthsites.io and HOT education facilities (HDX, ODbL): registry cross-checks
# Overture Maps places and buildings come from download_overture.py.
# The PSA 2024 census workbook and the DOH facility registry are downloaded by hand into data/manual/.
#
# Not built yet: arrives in PR 2.
set -euo pipefail

echo "src/01_collect_data/download_sources.sh: not built yet, arrives in PR 2" >&2
exit 2
