"""
Shared paths, study constants and helpers for the pipeline.

Every parameter the analysis uses lives here, so a change of threshold or speed is one
edit; docs/paper.md (section 4) explains each one. Home locations never go in this file:
they live in data/manual/homes.csv, which is gitignored.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"  # downloads from 01_collect_data.sh (gitignored)
MANUAL = ROOT / "data" / "manual"  # hand downloads and the private home points (gitignored)
WORK = ROOT / "data" / "work"  # large intermediates (gitignored)
DERIVED = ROOT / "data" / "derived"  # small tables the paper cites (committed)
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"
MAP_DATA = ROOT / "docs" / "map" / "data"

# Private home points for the home lens (one row per study barangay: pcode, lat, lon).
# Gitignored with the rest of data/manual/, read only for the private check, never published.
HOMES_FILE = MANUAL / "homes.csv"

# The three study barangays (PSGC codes as used by the OCHA COD-AB boundaries).
BARANGAYS = {
    "PH1303901136": {"name": "Barangay 136", "district": "Tondo", "city": "City of Manila", "lived": "born and raised"},
    "PH1307404055": {"name": "Loyola Heights", "city": "Quezon City", "lived": "two years of college"},
    "PH1307403013": {"name": "Oranbo", "city": "City of Pasig", "lived": "now"},
}

# Walking. 4.2 km/h is close to the observed Metro Manila pace of 70.62 m/min (Tolentino and Sigua 2022).
WALK_SPEED_KMH = 4.2
WALK_SPEEDS_SENSITIVITY_KMH = (3.6, 4.2, 4.8)
THRESHOLDS_MIN = (5, 10, 15, 20)
SUFFICIENCY_MIN = 10  # the 10-minute minimum, about 700 m
CHECK_WALKSHED_MIN = (10, 15, 20)  # equal walk-sheds around each barangay's population centre

# Transit, after UN SDG 11.2.1: 500 m to a bus or jeepney stop or route, 1 km to LRT or MRT.
TRANSIT_LOW_CAPACITY_M = 500
TRANSIT_HIGH_CAPACITY_M = 1000
JEEPNEY_ROUTES_COUNT_AS_STOPS = True

# Measures and grids.
E2SFCA_CATCHMENT_MIN = 15
COVERAGE_MIN = 15
H3_RESOLUTION = 10  # display and reporting cells, about 0.015 km2
H3_RESOLUTION_CHECK = 9  # the coarser origins of sensitivity check 06
FRINGE_KM = 2.0  # services this far beyond Metro Manila still count

# The study box: Metro Manila (COD-AB region PH13) plus FRINGE_KM on every side, rounded
# outward to 0.01 degrees, as (west, south, east, north). Overture is downloaded and the
# walking network built inside it; build_tables.py checks that it still holds the fringe.
STUDY_BOX = (120.88, 14.33, 121.16, 14.81)
UTM = "EPSG:32651"  # WGS 84 / UTM zone 51N, for areas and distances in metres

# Sources.
OVERTURE_RELEASE = "2026-10-21.0"
WORLDPOP_YEAR = 2024
OVERTURE_MIN_CONFIDENCE = 0.5
OVERTURE_CONFIDENCE_SENSITIVITY = (0.3, 0.5, 0.7)  # check 08; places below the lowest are not kept
DEDUPE_M = 50
# Schools, hospitals and markets are big: two records of one up to this far apart are the same
# place when their names agree (their points can sit at different corners of one campus).
CAMPUS_DEDUPE_M = 150
CAMPUS_CATEGORIES = ("palengke", "hospital", "public_elementary", "public_high")
OPEN_SPACE_MIN_HA = 0.1
OPEN_SPACE_ACCESS_SPACING_M = 25  # open space is reached at points this far apart round its edge
MIN_BUILDING_M2 = 10  # smaller footprints (sheds, kiosks, mapping slivers) hold no one

BOUNDARIES = RAW / "phl_admin_boundaries.gdb.zip"
WORLDPOP_TIF = RAW / "phl_pop_2024_100m.tif"
GHS_POP_ZIP = RAW / "ghs_pop_e2025_100m_r8_c30.zip"
OSM_PBF = RAW / "philippines-latest.osm.pbf"
OVERTURE_PLACES = RAW / "overture_places.parquet"
OVERTURE_BUILDINGS = RAW / "overture_buildings.parquet"
HEALTHSITES_CSV = RAW / "healthsites_philippines.csv"
DEPED_SCHOOLS = RAW / "deped_schools_osmapaaralan_2019.tsv"
HOT_EDUCATION = RAW / "hotosm_education_facilities.parquet"
CENSUS_NCR_XLSX = MANUAL / "popcen2024" / "ncr.xlsx"
DOH_NHFR_FOLDER = MANUAL / "doh_nhfr"  # optional hand download; see docs/data-quality.md

# The nine service categories, grouped by the social functions of Moreno et al. (2021).
SERVICES = {
    "supplying": ("food_retail", "palengke", "pharmacy"),
    "caring": ("primary_care", "hospital"),
    "learning": ("public_elementary", "public_high"),
    "enjoying": ("open_space",),
    "moving": ("transit",),
}
CATEGORIES = tuple(c for cats in SERVICES.values() for c in cats)


def metres(minutes, speed_kmh=WALK_SPEED_KMH):
    """Distance walked in `minutes` at `speed_kmh`."""
    return speed_kmh * 1000 / 60 * minutes


def read_ncr_barangays(columns=None):
    """The Metro Manila barangay polygons (COD-AB admin level 4, region PH13), sorted by pcode."""
    import geopandas as gpd  # imported here so the tests need no geospatial stack

    if columns is not None:  # the filter column must be read, or the filter matches nothing
        columns = list(dict.fromkeys([*columns, "adm1_pcode"]))
    g = gpd.read_file(f"zip://{BOUNDARIES}", layer="phl_admin4", columns=columns, where="adm1_pcode = 'PH13'")
    if len(g) < 1700:
        raise ValueError(f"expected the 1,712 Metro Manila barangays of COD-AB v03, read {len(g)}")
    return g.sort_values("adm4_pcode").reset_index(drop=True)


def write_json(path, obj):
    """Write `obj` as indented JSON with a final newline, and say so."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")


def require(*paths, how):
    """Stop with a clear message when an input file is missing."""
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.exists()]
    if missing:
        sys.exit(f"missing input: {', '.join(missing)}\n{how}")


def not_built(script, pr):
    """Stop a pipeline script that is still a stub, naming the PR that builds it."""
    print(f"{Path(script).resolve().relative_to(ROOT)}: not built yet, arrives in PR {pr}", file=sys.stderr)
    raise SystemExit(2)


for _d in (WORK, DERIVED):
    _d.mkdir(parents=True, exist_ok=True)
