#!/usr/bin/env python3
"""
Place people in buildings: each barangay's 2024 census count spread over its WorldPop 2024
100 m cells, then over the residential building footprints in each cell.

Three layers, coarse to fine (dasymetric mapping):
  1. the census fixes how many people live in each barangay;
  2. WorldPop's 100 m grid says which parts of the barangay are lived in;
  3. inside a 100 m cell, people go to residential buildings in proportion to footprint area.
A residential building is an Overture footprint of at least MIN_BUILDING_M2 that is tagged
residential or not tagged at all (about 4 in 5 are untagged); commercial, industrial,
education, civic, religious, medical and other tagged buildings, garages and underground
structures get no one. A barangay whose buildings all sit in cells WorldPop leaves empty
spreads its count by footprint area alone; one with no residential building uses any building,
and one with no building at all gets one origin at its interior point.

The same placement with the JRC GHS-POP 2025 100 m grid in place of WorldPop gives
`people_ghs`, for sensitivity check 09.

  data/work/origins.parquet              one row per residential building: pcode, people,
                                         people_ghs, location, WorldPop cell and H3 cells
  data/work/people_by_barangay.parquet   per barangay: buildings, WorldPop and GHS-POP sums
  data/work/people_stats.json            coverage checks, gathered by build_tables.py

Every residential building in the three study barangays becomes an origin weighted by its
people; the rest of Metro Manila gives the context percentiles.

Run after read_census_2024.py:  python src/02_build_tables/place_people.py
"""

import sys
from pathlib import Path

import duckdb
import h3
import numpy as np
import pandas as pd
import pyproj
import rasterio
import rasterio.features
import rasterio.windows
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import (
    BARANGAYS,
    GHS_POP_ZIP,
    H3_RESOLUTION,
    H3_RESOLUTION_CHECK,
    MIN_BUILDING_M2,
    OVERTURE_BUILDINGS,
    ROOT,
    WORK,
    WORLDPOP_TIF,
    read_ncr_barangays,
    require,
    write_json,
)

require(WORK / "census_2024.parquet", how="Run src/02_build_tables/read_census_2024.py first.")
require(OVERTURE_BUILDINGS, WORLDPOP_TIF, GHS_POP_ZIP, how="Run ./01_collect_data.sh first.")

NOT_RESIDENTIAL_CLASS = ("garage", "garages", "parking", "carport", "shed")
GHS_TIF = f"zip://{GHS_POP_ZIP}!GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R8_C30.tif"

census = pd.read_parquet(WORK / "census_2024.parquet").set_index("pcode")
geo = read_ncr_barangays(columns=["adm4_pcode"]).set_index("adm4_pcode")
assert geo.index.equals(census.index.sort_values()), "census and boundaries hold different barangays"
polys = geo.geometry.values
pcodes = geo.index.values
tree = shapely.STRtree(polys)
W, S, E, N = geo.total_bounds


def barangay_of(lon, lat):
    """The barangay index each point falls in, or -1 (a point on a shared edge goes to one)."""
    pi, bi = tree.query(shapely.points(lon, lat), predicate="intersects")
    out = np.full(len(lon), -1)
    first = ~pd.Series(pi).duplicated().values
    out[pi[first]] = bi[first]
    return out


# ---------------------------------------------------------------------------
# 1. Buildings in Metro Manila
# ---------------------------------------------------------------------------
con = duckdb.connect()
bld = con.sql(f"""
    SELECT id, subtype, class, num_floors, dataset, area_m2, lon, lat,
           (coalesce(subtype, 'residential') = 'residential'
            AND coalesce(class, '') NOT IN {NOT_RESIDENTIAL_CLASS}
            AND NOT coalesce(is_underground, false)
            AND area_m2 >= {MIN_BUILDING_M2}) AS residential
    FROM read_parquet('{OVERTURE_BUILDINGS}')
    WHERE lon BETWEEN {W} AND {E} AND lat BETWEEN {S} AND {N}
""").df()
bld["b"] = barangay_of(bld.lon.values, bld.lat.values)
bld = bld[bld.b >= 0].reset_index(drop=True)
bld["pcode"] = pcodes[bld.b]
print(f"Overture buildings in Metro Manila: {len(bld):,}, residential {bld.residential.sum():,}")


# ---------------------------------------------------------------------------
# 2. The population grids under each building, and their Metro Manila totals
# ---------------------------------------------------------------------------
def read_grid(path):
    """The grid window over Metro Manila, its transform, and each building's cell."""
    with rasterio.open(path) as src:
        to_grid = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        corners = np.array(to_grid.transform([W, E, W, E], [S, S, N, N])).T
        window = rasterio.windows.from_bounds(*corners.min(0), *corners.max(0), transform=src.transform)
        window = window.round_offsets().round_lengths()
        window = rasterio.windows.Window(window.col_off - 2, window.row_off - 2, window.width + 4, window.height + 4)
        grid = src.read(1, window=window, boundless=True, fill_value=0).astype("float64")
        transform = src.window_transform(window)
        crs = src.crs
    grid[~np.isfinite(grid) | (grid < 0)] = 0
    x, y = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(bld.lon.values, bld.lat.values)
    rows, cols = rasterio.transform.rowcol(transform, x, y)
    rows, cols = np.asarray(rows), np.asarray(cols)
    # Barangay of every cell centre, for each grid's own Metro Manila total
    cell_b = rasterio.features.rasterize(
        (
            (g, i + 1)
            for i, g in enumerate(shapely.transform(polys, lambda c: np.column_stack(to_grid.transform(*c.T))))
        ),
        out_shape=grid.shape,
        transform=transform,
        dtype="int32",
    )
    return grid, rows, cols, cell_b - 1


def place(grid, rows, cols, cell_b, label):
    """People per building from one population grid; returns (people, method, stats)."""
    value = grid[rows, cols]
    cell = rows.astype(np.int64) * grid.shape[1] + cols
    res = bld.residential.values
    area = np.where(res, bld.area_m2.values, 0.0)
    cell_area = pd.Series(area).groupby(cell).transform("sum").values
    w_grid = np.where(res & (cell_area > 0), value * area / np.where(cell_area > 0, cell_area, 1), 0.0)
    frame = pd.DataFrame({"pcode": bld.pcode.values, "w_grid": w_grid, "w_area": area, "w_any": bld.area_m2.values})
    sums = frame.groupby("pcode")[["w_grid", "w_area", "w_any"]].transform("sum")
    method = np.select(
        [sums.w_grid > 0, sums.w_area > 0, sums.w_any > 0],
        [f"buildings x {label}", "residential buildings by area", "any building by area"],
        "none",
    )
    weight = np.select(
        [sums.w_grid > 0, sums.w_area > 0, sums.w_any > 0],
        [frame.w_grid / sums.w_grid, frame.w_area / sums.w_area, frame.w_any / sums.w_any],
        0.0,
    )
    people = census.people.reindex(bld.pcode).values * weight
    # Grid people in Metro Manila, and the share of them in a cell holding a residential building
    in_ncr = cell_b >= 0
    has_bld = np.zeros(grid.size, dtype=bool)
    has_bld[cell[res]] = True
    has_bld = has_bld.reshape(grid.shape)
    stats = {
        "grid_people_in_metro_manila": round(float(grid[in_ncr].sum())),
        "grid_people_in_cells_with_a_residential_building": round(float(grid[in_ncr & has_bld].sum())),
        "share_in_cells_with_a_residential_building": round(
            float(grid[in_ncr & has_bld].sum() / grid[in_ncr].sum()), 4
        ),
        "grid_by_barangay": pd.Series(grid[in_ncr]).groupby(cell_b[in_ncr]).sum().rename(index=dict(enumerate(pcodes))),
    }
    return people, method, cell, stats


wp_grid, wp_rows, wp_cols, wp_cell_b = read_grid(WORLDPOP_TIF)
people, method, wp_cell, wp_stats = place(wp_grid, wp_rows, wp_cols, wp_cell_b, "WorldPop")
gh_grid, gh_rows, gh_cols, gh_cell_b = read_grid(GHS_TIF)
people_ghs, method_ghs, _, gh_stats = place(gh_grid, gh_rows, gh_cols, gh_cell_b, "GHS-POP")
bld["people"], bld["method"], bld["people_ghs"], bld["wp_cell"] = people, method, people_ghs, wp_cell


# ---------------------------------------------------------------------------
# 3. Origins: residential buildings with people, plus the fallbacks
# ---------------------------------------------------------------------------
keep = (bld.people > 0) | (bld.people_ghs > 0)
origins = bld.loc[keep, ["id", "pcode", "lon", "lat", "area_m2", "num_floors", "dataset", "people", "people_ghs"]]
origins = origins.rename(columns={"id": "origin_id"}).assign(method=method[keep.values], wp_cell=wp_cell[keep.values])
placed = set(origins.pcode)
empty = census[(census.people > 0) & ~census.index.isin(placed)]
if len(empty):
    pts = geo.geometry[empty.index].representative_point()
    origins = pd.concat(
        [
            origins,
            pd.DataFrame(
                {
                    "origin_id": "barangay:" + empty.index,
                    "pcode": empty.index,
                    "lon": pts.x.values,
                    "lat": pts.y.values,
                    "people": empty.people.values,
                    "people_ghs": empty.people.values,
                    "method": "barangay point",
                }
            ),
        ],
        ignore_index=True,
    )
origins["h3_10"] = [h3.latlng_to_cell(la, lo, H3_RESOLUTION) for la, lo in zip(origins.lat, origins.lon, strict=True)]
origins["h3_9"] = [h3.cell_to_parent(c, H3_RESOLUTION_CHECK) for c in origins.h3_10]
origins = origins.sort_values(["pcode", "origin_id"]).reset_index(drop=True)
origins.to_parquet(WORK / "origins.parquet", index=False)
print(f"wrote {(WORK / 'origins.parquet').relative_to(ROOT)}: {len(origins):,} origins")

total = float(census.people.sum())
for col in ("people", "people_ghs"):
    gap = origins[col].sum() - total
    assert abs(gap) < 1, f"{col} sums to {origins[col].sum():,.1f}, census {total:,.0f}"

# ---------------------------------------------------------------------------
# 4. Per-barangay counts and the checks
# ---------------------------------------------------------------------------
by_b = pd.DataFrame(index=pd.Index(pcodes, name="pcode"))
by_b["buildings"] = bld.groupby("pcode").size()
by_b["residential_buildings"] = bld[bld.residential].groupby("pcode").size()
by_b["origins"] = origins.groupby("pcode").size()
by_b["placement"] = origins.groupby("pcode").method.first()
by_b["worldpop_2024"] = wp_stats.pop("grid_by_barangay")
by_b["ghs_pop_2025"] = gh_stats.pop("grid_by_barangay")
by_b = by_b.fillna({"buildings": 0, "residential_buildings": 0, "origins": 0, "worldpop_2024": 0, "ghs_pop_2025": 0})
by_b.reset_index().to_parquet(WORK / "people_by_barangay.parquet", index=False)

study = {}
for pcode, place_ in BARANGAYS.items():
    o = origins[origins.pcode == pcode]
    study[place_["name"]] = {
        "people": round(float(o.people.sum())),
        "buildings": int(by_b.buildings[pcode]),
        "residential_buildings": int(by_b.residential_buildings[pcode]),
        "origins": len(o),
        "placement": by_b.placement[pcode],
        "people_per_origin_median": round(float(o.people.median()), 1),
        "people_in_largest_origin": round(float(o.people.max()), 1),
        "share_in_largest_10_origins": round(float(o.people.nlargest(10).sum() / o.people.sum()), 3),
        "worldpop_2024": round(float(by_b.worldpop_2024[pcode])),
        "ghs_pop_2025": round(float(by_b.ghs_pop_2025[pcode])),
    }
stats = {
    "census_people": round(total),
    "buildings_in_metro_manila": len(bld),
    "residential_buildings": int(bld.residential.sum()),
    "buildings_by_source": {k: int(v) for k, v in bld[bld.residential].dataset.value_counts().items()},
    "origins": len(origins),
    "origins_by_method": {k: int(v) for k, v in origins.method.value_counts().items()},
    "people_by_method": {k: round(float(v)) for k, v in origins.groupby("method").people.sum().items()},
    "barangays_by_method": {k: int(v) for k, v in by_b.placement.fillna("no people").value_counts().items()},
    "people_ghs_by_method": {k: int(v) for k, v in pd.Series(method_ghs[keep.values]).value_counts().items()},
    "worldpop": wp_stats,
    "ghs_pop": gh_stats,
    "study_barangays": study,
}
write_json(WORK / "people_stats.json", stats)
print(
    f"people placed: {origins.people.sum():,.0f} of {total:,.0f}; WorldPop people in a cell with a residential "
    f"building {wp_stats['share_in_cells_with_a_residential_building']:.1%}"
)
for name, s in study.items():
    print(f"  {name}: {s['people']:,} people in {s['origins']:,} buildings ({s['placement']})")
