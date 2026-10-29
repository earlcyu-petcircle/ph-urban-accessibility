"""
Shared paths, study constants, colours and the DuckDB helper.

Every step reads and writes under data/: raw downloads in data/raw/ and large
intermediates in data/work/ (both gitignored), small committed outputs in
data/derived/. SQL lives in sql/ and is run through run_sql(), which fills in
${NAME} placeholders from the constants below.
"""
from pathlib import Path
from string import Template

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"          # downloads from fetch_data.sh (gitignored)
WORK = ROOT / "data" / "work"        # large intermediates (gitignored)
DERIVED = ROOT / "data" / "derived"  # small tables and the barangay scores (committed)
SQL = ROOT / "sql"
DOCS = ROOT / "docs"                 # the interactive map, ready for GitHub Pages
FIGURES = ROOT / "figures"
for _d in (WORK, DERIVED, DOCS, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)

OVERTURE_RELEASE = "2026-10-21.0"
OVERTURE_S3 = f"s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}"
BOUNDARIES = f"/vsizip/{RAW / 'phl_admin_boundaries.gdb.zip'}"
OSM_PBF = RAW / "philippines-latest.osm.pbf"

# Study box: Metro Manila plus at least 1.5 km on every land side, so a service
# just across a city border still counts for the people who live near it.
BBOX = dict(XMIN=120.85, XMAX=121.20, YMIN=14.30, YMAX=14.82)

# Walking at 4.5 km/h is 75 m a minute.
WALK_M_PER_MIN = 75
MINUTES = (5, 10, 15)
THRESHOLDS_M = {m: m * WALK_M_PER_MIN for m in MINUTES}  # 375, 750, 1,125 m

# Overture places below this confidence are mostly stale or duplicate records.
MIN_CONFIDENCE = 0.5

SERVICES = ["grocery", "health", "parks", "transit", "schools"]
SERVICE_LABELS = {
    "composite": "All services",
    "grocery": "Grocery",
    "health": "Healthcare",
    "parks": "Parks",
    "transit": "Transit",
    "schools": "Schools",
}

# The three places lived, at barangay level only (never a building or address).
# Tondo is the whole Tondo district (PSGC sub-municipality 133901, Tondo I/II):
# PhilPost assigns zip 1013 (Tondo North) and 1012 (Tondo South) by district, not
# by barangay, so the 1013 part cannot be drawn from barangay lists.
PLACES_LIVED = {
    "tondo": dict(label="Tondo, Manila", years="birth to 18",
                  note="Born and raised here, zip 1013 (Tondo North). Outline is the whole Tondo district, "
                       "since PhilPost zips do not map cleanly onto barangays."),
    "loyola": dict(label="Loyola Heights, Quezon City", years="two years of college",
                   note="Two years of college along Katipunan, near Ateneo de Manila, before the pandemic."),
    "oranbo": dict(label="Oranbo, Pasig", years="now",
                   note="Home now, zip 1600, the barangay around Capitol Commons and Estancia."),
}

# Muted Archive palette. Scores use six fixed classes, the same for every service so
# colours compare across services: terracotta (poor access) -> sand -> slate-teal (good).
BG, SURFACE, INK, MUTED, FAINT, ACCENT, RULE = (
    "#F1EBDD", "#F8F3E8", "#292216", "#665B45", "#8B8069", "#96700F", "#C2B597")
SCORE_BREAKS = [40, 55, 70, 85, 95]
SCORE_COLOURS = ["#8A4B2E", "#B9784A", "#D8B47E", "#C9CDB2", "#7FA6A0", "#3E6B66"]


def connect(path=":memory:"):
    con = duckdb.connect(str(path))
    for ext in ("spatial", "httpfs"):
        con.install_extension(ext)
        con.load_extension(ext)
    con.sql("SET s3_region = 'us-west-2'; SET geometry_always_xy = true;")
    return con


def sql_text(name, **extra):
    """Read sql/<name>.sql and fill its ${...} placeholders."""
    params = dict(BBOX, OVERTURE=OVERTURE_S3, WORK=str(WORK), RAW=str(RAW), DERIVED=str(DERIVED),
                  MIN_CONFIDENCE=MIN_CONFIDENCE, T5=THRESHOLDS_M[5], T10=THRESHOLDS_M[10],
                  T15=THRESHOLDS_M[15], OSM_PBF=str(OSM_PBF))
    params.update(extra)
    return Template((SQL / f"{name}.sql").read_text()).substitute(params)


def run_sql(con, name, **extra):
    return con.sql(sql_text(name, **extra))
