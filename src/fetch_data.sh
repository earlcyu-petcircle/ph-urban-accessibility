#!/usr/bin/env bash
# Download the four file-based inputs into data/raw/.
# No API keys, no logins. Run from the repo root.
# Overture (places, buildings, land use) is not downloaded here: src/extract.py
# reads it straight from Overture's public S3 bucket with DuckDB.
# Files that already exist are kept; pass --refresh to download everything again
# (OpenStreetMap changes daily, so a refresh moves the transit and network inputs).
set -euo pipefail

RAW="data/raw"
UA="metro-manila-accessibility/1.0 (open-data spatial research; https://github.com/earlcyu-petcircle/metro-manila-accessibility)"
REFRESH=0
[ "${1:-}" = "--refresh" ] && REFRESH=1
mkdir -p "$RAW"

fetch() {  # fetch <output file> <url>
  local out="$RAW/$1"
  if [ -s "$out" ] && [ "$REFRESH" = 0 ]; then
    echo "keep     $out"
    return
  fi
  echo "download $out"
  curl -fsSL --retry 5 --retry-all-errors -H "User-Agent: $UA" "$2" -o "$out.part"
  mv "$out.part" "$out"
}

# 1. Barangay boundaries: PSA / NAMRIA COD-AB via HDX (version v03, valid from 13 Feb 2025), about 360 MB.
fetch phl_admin_boundaries.gdb.zip \
  "https://data.humdata.org/dataset/caf116df-f984-4deb-85ca-41b349d3f313/resource/3fa0dbcf-e07d-4506-9821-ba15baa6da07/download/phl_admin_boundaries.gdb.zip"

# 2. Barangay population: PSA 2020 Census of Population and Housing, via OCHA Philippines on HDX.
fetch phl_census2020_brgy.xlsx \
  "https://data.humdata.org/dataset/186f5609-e970-4165-86a0-a87a770532e2/resource/dd6fb33a-a91b-450c-a0f8-0b760a75458e/download/2020-census-total-popn-brgy_adm4_new-pcode.xlsx"

# 3. Gridded population: WorldPop Global2 R2025A, 2020, constrained, 100 m.
fetch phl_worldpop_2020_cn_100m.tif \
  "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2020/PHL/v1/100m/constrained/phl_pop_2020_CN_100m_R2025A_v1.tif"

# 4. OpenStreetMap: Geofabrik's Philippines extract (walking network, transit), about 610 MB.
fetch philippines-latest.osm.pbf "https://download.geofabrik.de/asia/philippines-latest.osm.pbf"

# Record the OSM snapshot the run used; the README quotes it.
if [ ! -s "$RAW/osm_snapshot.txt" ] || [ "$REFRESH" = 1 ]; then
  curl -fsSL -H "User-Agent: $UA" "https://download.geofabrik.de/asia/philippines-updates/state.txt" \
    | sed -n 's/^timestamp=//p' | tr -d '\\' > "$RAW/osm_snapshot.txt"
fi
echo "OSM snapshot: $(cat "$RAW/osm_snapshot.txt")"
