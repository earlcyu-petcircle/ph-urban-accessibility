"""
Shared paths, study constants and helpers for the pipeline.

Every parameter the analysis uses lives here, so a change of threshold or speed is one
edit; docs/paper.md (section 4) explains each one. Home locations never go in this file:
they live in data/manual/homes.csv, which is gitignored.
"""

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
FRINGE_KM = 2.0  # services this far beyond Metro Manila still count

# Sources.
OVERTURE_RELEASE = "2026-10-21.0"
WORLDPOP_YEAR = 2024
OVERTURE_MIN_CONFIDENCE = 0.5
DEDUPE_M = 50
OPEN_SPACE_MIN_HA = 0.1

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


def not_built(script, pr):
    """Stop a pipeline script that is still a stub, naming the PR that builds it."""
    print(f"{Path(script).resolve().relative_to(ROOT)}: not built yet, arrives in PR {pr}", file=sys.stderr)
    raise SystemExit(2)
