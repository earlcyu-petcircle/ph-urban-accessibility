#!/usr/bin/env python3
"""
Build the small committed tables the paper cites, and the numbers behind docs/data-quality.md.

  data/derived/barangays.csv      one row per Metro Manila barangay: people, area, density, study flag
  data/derived/data_quality.json  snapshots, row counts, licences and completeness for every layer

It also checks that the study box still holds Metro Manila and its fringe.
Run after build_walk_network.py:  python src/02_build_tables/build_tables.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import (
    BARANGAYS,
    CATEGORIES,
    DERIVED,
    FRINGE_KM,
    OVERTURE_RELEASE,
    ROOT,
    STUDY_BOX,
    UTM,
    WORK,
    read_ncr_barangays,
    require,
    write_json,
)

STEP_OUTPUTS = {
    "read_census_2024.py": WORK / "census_2024.parquet",
    "place_people.py": WORK / "people_stats.json",
    "build_services.py": WORK / "services_stats.json",
    "build_walk_network.py": WORK / "walk_stats.json",
}
for script, path in STEP_OUTPUTS.items():
    require(path, how=f"Run src/02_build_tables/{script} first.")

geo = read_ncr_barangays(columns=["adm4_pcode", "valid_on", "version"]).to_crs(UTM)
fringe = geo.union_all().buffer(FRINGE_KM * 1000)
fringe_box = pd.Series(geo.set_geometry([fringe] * len(geo)).to_crs(4326).total_bounds, index=list("WSEN"))
W, S, E, N = STUDY_BOX
if not (W <= fringe_box.W and S <= fringe_box.S and fringe_box.E <= E and fringe_box.N <= N):
    sys.exit(f"STUDY_BOX {STUDY_BOX} no longer holds Metro Manila plus {FRINGE_KM} km: {fringe_box.round(4).tolist()}")

# ---------------------------------------------------------------------------
# 1. barangays.csv
# ---------------------------------------------------------------------------
census = pd.read_parquet(WORK / "census_2024.parquet")
people = pd.read_parquet(WORK / "people_by_barangay.parquet")
b = census.merge(people, on="pcode", how="left", validate="1:1")
b["area_km2"] = b.pcode.map(dict(zip(geo.adm4_pcode, geo.area / 1e6, strict=True))).round(4)
b["people"] = b.people.round().astype(int)
b["people_per_km2"] = (b.people / b.area_km2).round().astype(int)
b["study"] = b.pcode.map({p: v["name"] for p, v in BARANGAYS.items()}).fillna("")
b["tondo_district"] = b.district.fillna("").str.startswith("Tondo")
b["district"] = b.district.fillna("")
for col in ("worldpop_2024", "ghs_pop_2025"):
    b[col] = b[col].round().astype(int)
for col in ("buildings", "residential_buildings", "origins"):
    b[col] = b[col].astype(int)
b = b.rename(columns={"match": "census_match"})
cols = [
    "pcode",
    "barangay",
    "city_pcode",
    "city",
    "district",
    "tondo_district",
    "study",
    "people",
    "census_match",
    "area_km2",
    "people_per_km2",
    "worldpop_2024",
    "ghs_pop_2025",
    "buildings",
    "residential_buildings",
    "origins",
]
b[cols].sort_values("pcode").to_csv(DERIVED / "barangays.csv", index=False)
print(f"wrote {(DERIVED / 'barangays.csv').relative_to(ROOT)}: {len(b):,} barangays")

# ---------------------------------------------------------------------------
# 2. data_quality.json
# ---------------------------------------------------------------------------
check = json.loads((DERIVED / "census_2024_check.json").read_text())
people_stats = json.loads((WORK / "people_stats.json").read_text())
services = json.loads((WORK / "services_stats.json").read_text())
walk = json.loads((WORK / "walk_stats.json").read_text())
svc = pd.read_parquet(WORK / "services.parquet")
default = svc[svc.in_default & svc.pcode.notna()]

# Where the census count and WorldPop disagree most: usually a boundary drawn differently in
# COD-AB and in the 2024 census (the EMBO barangays), which crowds people into few buildings
mismatch = b[b.people > 3 * b.worldpop_2024.clip(lower=1)]
origin_people = pd.read_parquet(WORK / "origins.parquet", columns=["people"]).people
origins_max, origins_over_500 = origin_people.max(), (origin_people > 500).sum()

study = {}
for pcode, place in BARANGAYS.items():
    row = b[b.pcode == pcode].iloc[0]
    study[place["name"]] = {
        "pcode": pcode,
        "city": row.city,
        "people": int(row.people),
        "area_km2": float(row.area_km2),
        "people_per_km2": int(row.people_per_km2),
        **{k: v for k, v in people_stats["study_barangays"][place["name"]].items() if k != "people"},
        "services_inside": {
            c: int(default[(default.pcode == pcode) & (default.category == c)].shape[0]) for c in CATEGORIES
        },
    }

quality = {
    "snapshots": {
        "census": "PSA 2024 Census of Population, 1 July 2024",
        "boundaries": f"OCHA COD-AB Philippines {geo.version.iloc[0]}, valid from {geo.valid_on.iloc[0]:%Y-%m-%d}",
        "worldpop": "WorldPop R2025A, 2024, constrained, 100 m",
        "ghs_pop": "JRC GHS-POP R2023A, 2025 epoch, 100 m, tile R8_C30",
        "overture": f"Overture Maps release {OVERTURE_RELEASE}",
        "openstreetmap": f"Geofabrik Philippines extract, replication time {walk['osm_snapshot']}",
        "deped": "OSMaPaaralan (DepEd MaPaaralan school list, cleaned by OpenStreetMap Philippines), 2019",
    },
    "licences": {
        "census": "PSA publication",
        "boundaries": "CC BY-IGO",
        "worldpop": "CC BY 4.0",
        "ghs_pop": "CC BY 4.0",
        "overture_buildings": "ODbL",
        "overture_places": "CDLA Permissive 2.0 and per-source terms",
        "openstreetmap": "ODbL",
        "deped": "DepEd data, published for OpenStreetMap use; not redistributed here",
        "hot_education": "ODbL",
    },
    "study_box": {"west_south_east_north": list(STUDY_BOX), "fringe_bounds": fringe_box.round(4).tolist()},
    "census": {
        k: check[k]
        for k in (
            "census_barangays",
            "census_total",
            "table_b_ncr_total",
            "codab_barangays",
            "match",
            "census_people_matched",
            "census_people_not_placed",
            "tondo_district_barangays",
            "problems",
        )
    },
    "people": {k: v for k, v in people_stats.items() if k != "study_barangays"}
    | {
        "people_per_origin_max": round(float(origins_max), 1),
        "origins_over_500_people": int(origins_over_500),
        "barangays_census_over_3x_worldpop": {
            "barangays": len(mismatch),
            "people": int(mismatch.people.sum()),
            "largest": mismatch.nlargest(10, "people")[
                ["pcode", "barangay", "city", "people", "worldpop_2024"]
            ].to_dict("records"),
        },
    },
    "services": services,
    "walking_network": walk,
    "hand_downloads": {
        "census_ncr_workbook": "used",
        "doh_nhfr": "not saved; no DOH registry match or hospital beds in this build"
        if services["doh_registry"] is None
        else "used",
        "healthsites": "not downloaded (HDX bot challenge); check skipped"
        if services["healthsites_check"] is None
        else "used",
    },
    "study_barangays": study,
}
write_json(DERIVED / "data_quality.json", quality)
for name, s in study.items():
    print(f"  {name}: {s['people']:,} people, {s['area_km2']} km2, {s['people_per_km2']:,} per km2")
