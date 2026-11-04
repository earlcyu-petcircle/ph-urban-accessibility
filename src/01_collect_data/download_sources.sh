#!/usr/bin/env bash
# Download the open datasets into data/raw/ (gitignored).
# No API keys, no logins, no proprietary data. Run from the repo root.
# Files that already exist are kept; pass --refresh to download everything again
# (OpenStreetMap changes daily, so a refresh can change counts).
# About 1.1 GB in all; the Geofabrik extract and the COD-AB geodatabase are most of it.
#
# Overture Maps places and buildings come from download_overture.py, which reads the
# study area from the boundaries downloaded here.
# The PSA 2024 census workbook for the National Capital Region refuses scripted downloads and
# is saved by hand to data/manual/popcen2024/ncr.xlsx (docs/data-quality.md, "Getting the hand
# downloads"). The DOH National Health Facility Registry is not used: it refuses scripts and
# its export fails in a browser too.
# Two layers in docs/paper.md section 3 are not downloaded in this phase: the Mapillary
# imagery for the walk audit (PR 3, read through its API) and the map-only context layers
# (Relative Wealth Index, UP NOAH flood hazard; PR 4).
set -euo pipefail

RAW="data/raw"
UA="metro-manila-accessibility/1.0 (open-data spatial research; https://github.com/earlcyu-petcircle/metro-manila-accessibility)"
REFRESH=0
[ "${1:-}" = "--refresh" ] && REFRESH=1
mkdir -p "$RAW"

FAILED=()
OPTIONAL_FAILED=()
fetch() {  # fetch [--optional] <output file> <curl args...> <url>
  local optional=0
  [ "$1" = "--optional" ] && { optional=1; shift; }
  local out="$RAW/$1"; shift
  local url="${*: -1}"
  if [ -s "$out" ] && [ "$REFRESH" = 0 ]; then
    echo "keep     $out"
    return
  fi
  echo "download $out"
  curl -fsSL --retry 5 --retry-all-errors -H "User-Agent: $UA" "$@" -o "$out.part"
  # HDX sometimes answers scripts with a bot challenge: HTTP 202 and an empty body.
  if [ ! -s "$out.part" ]; then
    rm -f "$out.part"
    if [ "$optional" = 1 ]; then OPTIONAL_FAILED+=("$out <- $url"); else FAILED+=("$out <- $url"); fi
    echo "empty    $out (the server sent no file)" >&2
    return
  fi
  mv "$out.part" "$out"
}

# --- Boundaries and codes -------------------------------------------------------------

# 1. OCHA COD-AB Philippines (HDX, CC BY-IGO): region to barangay polygons from NAMRIA and
#    PSA, with PSGC-based pcodes. Files of 28 May 2026 (version v03).
fetch phl_admin_boundaries.gdb.zip --max-time 1800 \
  "https://data.humdata.org/dataset/caf116df-f984-4deb-85ca-41b349d3f313/resource/3fa0dbcf-e07d-4506-9821-ba15baa6da07/download/phl_admin_boundaries.gdb.zip"

# --- Population -----------------------------------------------------------------------

# 2. WorldPop R2025A 2024, 100 m, constrained to built settlement (CC BY 4.0). Only its
#    pattern is used: each barangay's census count is spread over its pixels.
fetch phl_pop_2024_100m.tif --max-time 900 \
  "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2024/PHL/v1/100m/constrained/phl_pop_2024_CN_100m_R2025A_v1.tif"

# 3. JRC GHS-POP R2023A, 2025 epoch, 100 m, Mollweide (CC BY 4.0): the second population
#    pattern for sensitivity check 09. Tile R8_C30 holds all of Metro Manila.
fetch ghs_pop_e2025_100m_r8_c30.zip --max-time 900 \
  "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E2025_GLOBE_R2023A_54009_100/V1-0/tiles/GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R8_C30.zip"

# 4. Census population by barangay: PSA 2024 Census of Population. psa.gov.ph answers
#    scripts with a bot check, so the NCR workbook is saved by hand (see the header).

# --- OpenStreetMap: services, open space, transit and the walking network --------------

# 5. Geofabrik Philippines extract (ODbL), about 610 MB. Geofabrik replaces it daily; the build
#    reads the snapshot time from the file's header and records it.
fetch philippines-latest.osm.pbf --max-time 3600 \
  "https://download.geofabrik.de/asia/philippines-latest.osm.pbf"

# --- Registries and completeness checks ----------------------------------------------

# 6. Healthsites.io Philippines (HDX, ODbL): a completeness check on the health layer. The
#    build runs without it, so a refused download only warns.
fetch --optional healthsites_philippines.csv --max-time 300 \
  "https://data.humdata.org/dataset/20e5069f-1eb8-465b-98c8-3442a62cd3f0/resource/b4a614ad-90f0-42b1-b484-7c1c4d910b94/download/philippines.csv"

# 7. The DepEd public-school registry: OSMaPaaralan, OpenStreetMap Philippines' cleaned copy of
#    DepEd's MaPaaralan school list (2019), listed on HDX by OCHA Philippines and served from
#    GitHub. Every public school with its DepEd school ID, ISCED level, 2015 enrolment and point.
fetch deped_schools_osmapaaralan_2019.tsv --max-time 300 \
  "https://raw.githubusercontent.com/OSMPH/deped_schools_db/master/data/2019/OSMaPaaralan_v2019-282-full.tsv"

# 8. HOT OpenStreetMap education facilities (HDX export, ODbL), a second school list.
fetch hotosm_education_facilities.parquet --max-time 600 \
  "https://production-raw-data-api.s3.amazonaws.com/ISO3/PHL/_layers/osm/education_facilities.parquet"

ls -la "$RAW"
if [ "${#OPTIONAL_FAILED[@]}" -gt 0 ]; then
  echo "" >&2
  echo "warning: optional download(s) came back empty; the build skips their checks:" >&2
  printf '  %s\n' "${OPTIONAL_FAILED[@]}" >&2
fi
if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "" >&2
  echo "${#FAILED[@]} download(s) came back empty. HDX (data.humdata.org) at times answers scripts with a" >&2
  echo "bot challenge; run this again later, or open each link in a browser and save the file under" >&2
  echo "the name on the left (docs/data-quality.md, 'Getting the hand downloads'):" >&2
  printf '  %s\n' "${FAILED[@]}" >&2
  exit 1
fi
