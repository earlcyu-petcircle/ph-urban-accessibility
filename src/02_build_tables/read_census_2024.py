#!/usr/bin/env python3
"""
Read the PSA 2024 Census of Population workbook for the National Capital Region, saved by
hand to data/manual/popcen2024/ncr.xlsx, and join its barangay counts to the COD-AB pcodes.

The workbook ("Table C - Population by Barangay", as of 1 July 2024) has one sheet per city
plus the regional "Table B". A city sheet starts with the city's total, then its barangays;
the City of Manila sheet stacks its districts the same way (district total, then barangays).
It carries names only, no PSGC codes, so the join to COD-AB is by name, after the method of
the ph-lottery-outlets study, in five passes:
  1. the same name in the same city (accents, "Sta.", roman numerals, "Poblacion" and
     bracketed alternatives evened out);
  2. the same once a trailing footnote number is dropped;
  3. the same name anywhere in Metro Manila (barangays that moved city, such as Makati's
     "EMBO" barangays, now in Taguig);
  4. a COD-AB barangay split since it was drawn (Caloocan's Barangay 176 into 176-A to 176-F)
     takes all its parts;
  5. a spelling variant in the same city: mutual best match, similarity 0.8 or more and the
     same numbers in both names.
A COD-AB barangay still unmatched takes a WorldPop 2024 share of the people its city left
unmatched, so city totals stay the census totals.

Checks, all in data/derived/census_2024_check.json:
  - every city and district total equals the sum of its barangays;
  - the barangays sum to the NCR total on "Table B" (14,001,751);
  - every census person lands on a COD-AB barangay, and the three study barangays match.

  data/work/census_2024.parquet          one row per COD-AB barangay: pcode, people, source
  data/derived/census_2024_check.json    totals, join passes and every unmatched name

Run after 01_collect_data.sh:  python src/02_build_tables/read_census_2024.py
"""

import difflib
import re
import sys
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import rasterio
import rasterio.features

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import (
    BARANGAYS,
    BOUNDARIES,
    CENSUS_NCR_XLSX,
    DERIVED,
    ROOT,
    WORK,
    WORLDPOP_TIF,
    read_ncr_barangays,
    require,
    write_json,
)

FIRST_DATA_ROW = 5  # below the title, date and two header rows
NCR_TABLE_B_TOTAL = 14_001_751  # NCR, 1 July 2024, on the workbook's Table B (checked below too)

require(
    CENSUS_NCR_XLSX,
    how="Download the PSA 2024 'Table C - Population by Barangay' workbook for NCR by hand "
    "(docs/data-quality.md, 'Getting the hand downloads').",
)
require(BOUNDARIES, WORLDPOP_TIF, how="Run ./01_collect_data.sh first.")


# ---------------------------------------------------------------------------
# 1. Read the workbook
# ---------------------------------------------------------------------------
def clean_area(name):
    """A city or district name without its footnote marks ("CITY OF MANILA *", "TAGUIG 2")."""
    return re.sub(r"(\s+\d{1,2})?\s*\*?\s*$", "", str(name)).strip()


def blocks_of(ws):
    """Runs of consecutive rows with a name in column B and a number in column D."""
    blocks, cur = [], []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < FIRST_DATA_ROW:
            continue
        name = row[1] if len(row) > 1 else None
        value = row[3] if len(row) > 3 else None
        if name is None or str(name).strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if not isinstance(value, int | float):
            raise ValueError(f"{ws.title!r} row {i + 1}: {name!r} has no population ({value!r})")
        cur.append((str(name).strip(), int(value)))
    if cur:
        blocks.append(cur)
    return blocks


warnings.filterwarnings("ignore", module="openpyxl")  # unparseable print headers
wb = openpyxl.load_workbook(CENSUS_NCR_XLSX, read_only=True)
rows, problems, table_b = [], [], None
for ws in wb.worksheets:
    if ws.title == "Table B":
        for r in ws.iter_rows(values_only=True):
            if r[0] and str(r[0]).startswith("NATIONAL CAPITAL REGION") and isinstance(r[5], int):
                table_b = r[5]  # the 1 July 2024 column
        continue
    blocks = blocks_of(ws)
    if not blocks:
        continue
    city, city_total = clean_area(blocks[0][0][0]), blocks[0][0][1]
    # A city sheet is one block, city first; Manila's city row stands alone, then its districts
    parts = blocks[1:] if len(blocks[0]) == 1 else [[(city, city_total)] + blocks[0][1:]]
    part_sum = 0
    for block in parts:
        (part, part_total), brgys = block[0], block[1:]
        if sum(v for _, v in brgys) != part_total:
            problems.append(f"{ws.title}: {part} total {part_total:,} != barangay sum {sum(v for _, v in brgys):,}")
        part_sum += part_total
        district = clean_area(part) if len(blocks[0]) == 1 else None
        rows += [(city, district, b, v) for b, v in brgys]
    if part_sum != city_total:
        problems.append(f"{ws.title}: city total {city_total:,} != sum of its parts {part_sum:,}")

census = pd.DataFrame(rows, columns=["city", "district", "barangay", "people"])
census["row"] = np.arange(len(census))
census_total = int(census.people.sum())
if table_b != NCR_TABLE_B_TOTAL:
    problems.append(f"Table B NCR total {table_b} != {NCR_TABLE_B_TOTAL:,}")
if census_total != table_b:
    problems.append(f"barangay sum {census_total:,} != Table B NCR total {table_b}")
print(f"POPCEN 2024 NCR: {len(census):,} barangays in {census.city.nunique()} cities, {census_total:,} people")


# ---------------------------------------------------------------------------
# 2. Join to COD-AB by name
# ---------------------------------------------------------------------------
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def _ascii(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def _saints(s):
    return re.sub(r"\bsto\b\.?", "santo", re.sub(r"\bsta\b\.?", "santa", s))


def _numerals(s):
    """Roman numerals as digits, so "Ligas II" and "Ligas 2" agree."""
    return re.sub(r"\b(" + "|".join(sorted(ROMAN, key=len, reverse=True)) + r")\b", lambda m: ROMAN[m.group(1)], s)


def norm_city(s):
    return re.sub(r"[^a-z0-9]", "", _saints(re.sub(r"\(.*?\)|\bcity of\b|\bcity\b", "", _ascii(s))))


def norm_brgy(s):
    s = re.sub(r"\(.*?\)|\bpoblacion\b|\bpob\b\.?|\bbarangay\b|\bbrgy\b|\bbgy\b", "", _ascii(s))
    return re.sub(r"[^a-z0-9]", "", _numerals(_saints(s)))


def loose(s):
    return re.sub(r"[^a-z0-9]", "", _numerals(_saints(re.sub(r"\(.*?\)", "", _ascii(s)))))


def strip_note(s):
    """A barangay name without a trailing footnote mark ("Saray 2", "East ²")."""
    return re.sub(r"\s*[¹²³⁰-⁹]+$|\s+\d{1,2}$", "", s.strip())


geo = read_ncr_barangays(columns=["adm4_pcode", "adm4_name", "adm3_pcode", "adm3_name", "area_sqkm"])
city_pcode = {norm_city(n): p for p, n in zip(geo.adm3_pcode, geo.adm3_name, strict=True)}
census["adm3_pcode"] = census.city.map(norm_city).map(city_pcode)
if census.adm3_pcode.isna().any():
    problems.append(f"census cities without a COD-AB city: {sorted(census[census.adm3_pcode.isna()].city.unique())}")
geo["scope"] = "NCR"
census["scope"] = "NCR"

match = {}  # adm4_pcode -> (census row, pass)
split = {}  # adm4_pcode -> the census rows it holds


def taken():
    return {r for r, _ in match.values()} | {r for rs in split.values() for r in rs}


def remaining(group_col):
    t = taken()
    return (
        geo[~geo.adm4_pcode.isin(match)].set_index("adm4_pcode").groupby(group_col),
        census[~census.row.isin(t)].set_index("row"),
    )


def match_unique(g_keys, c_keys, how):
    """Pair COD-AB and census barangays whose key is unique on both sides of one group."""
    gu = g_keys[~g_keys.duplicated(keep=False) & (g_keys != "")]
    cu = c_keys[~c_keys.duplicated(keep=False) & (c_keys != "")]
    lut = dict(zip(gu.values, gu.index, strict=True))
    for row, k in zip(cu.index, cu.values, strict=True):
        if k in lut:
            match[lut[k]] = (row, how)


KEYS = [(norm_brgy, norm_brgy), (loose, loose)]
KEYS_NOTE = [(gf, lambda s, cf=cf: cf(strip_note(s))) for gf, cf in KEYS]
for how, keys in (("name", KEYS), ("name_footnote", KEYS_NOTE)):  # passes 1 and 2
    for gf, cf in keys:
        g_left, c_left = remaining("adm3_pcode")
        c_by_city = dict(list(c_left.groupby("adm3_pcode")))
        for a3, g in g_left:
            if a3 in c_by_city:
                match_unique(g.adm4_name.map(gf), c_by_city[a3].barangay.map(cf), how)
for gf, cf in KEYS + KEYS_NOTE:  # pass 3
    g_left, c_left = remaining("scope")
    for _, g in g_left:
        match_unique(g.adm4_name.map(gf), c_left.barangay.map(cf), "name_ncr")
g_left, c_left = remaining("adm3_pcode")  # pass 4
c_by_city = dict(list(c_left.groupby("adm3_pcode")))
for a3, g in g_left:
    if a3 not in c_by_city:
        continue
    ck = c_by_city[a3].barangay.map(lambda s: norm_brgy(strip_note(s)))
    for gc, gk in zip(g.index, g.adm4_name.map(norm_brgy), strict=True):
        parts = ck[ck.str.fullmatch(re.escape(gk) + "[a-z]")] if gk else ck.iloc[:0]
        if len(parts) >= 2:
            split[gc] = list(parts.index)
            match[gc] = (parts.index[0], "name_split")
g_left, c_left = remaining("adm3_pcode")  # pass 5
c_by_city = dict(list(c_left.groupby("adm3_pcode")))
for a3, g in g_left:
    if a3 not in c_by_city:
        continue
    gk = dict(zip(g.index, g.adm4_name.map(loose), strict=True))
    ck = dict(zip(c_by_city[a3].index, c_by_city[a3].barangay.map(lambda s: loose(strip_note(s))), strict=True))
    ratio = {(gc, r): difflib.SequenceMatcher(None, gn, cn).ratio() for gc, gn in gk.items() for r, cn in ck.items()}
    best_g = {gc: max(ck, key=lambda r, gc=gc: ratio[gc, r]) for gc in gk}
    best_c = {r: max(gk, key=lambda gc, r=r: ratio[gc, r]) for r in ck}
    for gc, r in best_g.items():
        same_numbers = re.findall(r"\d+", gk[gc]) == re.findall(r"\d+", ck[r])
        if best_c[r] == gc and ratio[gc, r] >= 0.8 and same_numbers:
            match[gc] = (r, "fuzzy")

rows_of = {gc: [r] for gc, (r, _) in match.items()} | split
geo["people"] = geo.adm4_pcode.map({gc: int(census.people.iloc[rs].sum()) for gc, rs in rows_of.items()})
geo["match"] = geo.adm4_pcode.map({gc: how for gc, (_, how) in match.items()})
geo["census_name"] = geo.adm4_pcode.map({gc: "; ".join(census.barangay.iloc[rs]) for gc, rs in rows_of.items()})
geo["district"] = geo.adm4_pcode.map({gc: census.district.iloc[rs[0]] for gc, rs in rows_of.items()})
census["matched"] = census.row.isin(taken())


# ---------------------------------------------------------------------------
# 3. Unmatched COD-AB barangays share their city's unmatched people by WorldPop
# ---------------------------------------------------------------------------
gpoly = read_ncr_barangays(columns=["adm4_pcode"]).set_index("adm4_pcode").geometry
open_ = geo.people.isna()
with rasterio.open(WORLDPOP_TIF) as src:
    window = rasterio.windows.from_bounds(*gpoly.total_bounds, transform=src.transform)
    grid = src.read(1, window=window, boundless=True, fill_value=0)
    transform = src.window_transform(window)
grid = np.where(grid > 0, grid, 0)
wp = {}
for gc in geo.adm4_pcode[open_]:
    mask = rasterio.features.geometry_mask([gpoly[gc]], grid.shape, transform, invert=True, all_touched=True)
    wp[gc] = float(grid[mask].sum())
geo["worldpop_unmatched"] = geo.adm4_pcode.map(wp)
residual = census[~census.matched].groupby("adm3_pcode").people.sum()
for a3, g in geo[open_].groupby("adm3_pcode"):
    left = residual.get(a3, 0)
    weights = g.worldpop_unmatched.where(g.worldpop_unmatched > 0, 0)
    share = weights / weights.sum() if weights.sum() > 0 else pd.Series(1 / len(g), index=g.index)
    geo.loc[g.index, "people"] = left * share
    geo.loc[g.index, "match"] = "city_residual" if left else "none"
geo["people"] = geo.people.fillna(0)
geo["district"] = geo.district.where(geo.adm3_name == "City of Manila")

unplaced = int(census.loc[~census.matched, "people"].sum() - geo.loc[geo["match"] == "city_residual", "people"].sum())
if abs(geo.people.sum() - census_total) > 0.5:
    problems.append(f"people on COD-AB barangays {geo.people.sum():,.1f} != census {census_total:,}")
for pcode, place in BARANGAYS.items():
    hit = geo[geo.adm4_pcode == pcode]
    if hit.empty or hit["match"].iloc[0] not in ("name", "name_footnote"):
        problems.append(f"study barangay {place['name']} ({pcode}) did not match by name")
    elif place.get("district") and not str(hit.district.iloc[0]).startswith(place["district"]):
        problems.append(f"study barangay {place['name']} is in district {hit.district.iloc[0]}")

tondo = set(geo.adm4_pcode[geo.district.fillna("").str.startswith("Tondo")])
out = geo[["adm4_pcode", "adm4_name", "adm3_pcode", "adm3_name", "district", "people", "match", "census_name"]]
out = out.rename(
    columns={"adm4_pcode": "pcode", "adm4_name": "barangay", "adm3_pcode": "city_pcode", "adm3_name": "city"}
)
out.to_parquet(WORK / "census_2024.parquet", index=False)
print(f"wrote {(WORK / 'census_2024.parquet').relative_to(ROOT)}")

check = {
    "source": "PSA 2024 Census of Population, Table C - Population by Barangay, NCR, as of 1 July 2024",
    "file": str(CENSUS_NCR_XLSX.relative_to(ROOT)),
    "census_barangays": int(len(census)),
    "census_cities": int(census.city.nunique()),
    "census_total": census_total,
    "table_b_ncr_total": table_b,
    "codab_barangays": int(len(geo)),
    "match": {k: int(v) for k, v in geo["match"].value_counts().items()},
    "census_barangays_matched": int(census.matched.sum()),
    "census_people_matched": int(census.loc[census.matched, "people"].sum()),
    "census_unmatched": census.loc[~census.matched, ["city", "barangay", "people"]].to_dict("records"),
    "codab_unmatched": geo.loc[
        geo["match"].isin(["city_residual", "none"]), ["adm4_pcode", "adm4_name", "adm3_name", "people"]
    ]
    .round(1)
    .to_dict("records"),
    "codab_split": {geo.set_index("adm4_pcode").adm4_name[gc]: len(rs) for gc, rs in split.items()},
    "matched_on_another_name_or_city": geo.loc[
        geo["match"].isin(["name_ncr", "name_split", "fuzzy"]),
        ["adm4_pcode", "adm4_name", "adm3_name", "census_name", "match"],
    ].to_dict("records"),
    "census_people_not_placed": unplaced,
    "people_on_codab_barangays": round(float(geo.people.sum()), 1),
    "tondo_district_barangays": int(geo.district.fillna("").str.startswith("Tondo").sum()),
    "study_barangays": {
        place["name"]: {
            "pcode": pcode,
            "people": int(geo.loc[geo.adm4_pcode == pcode, "people"].iloc[0]),
            "match": geo.loc[geo.adm4_pcode == pcode, "match"].iloc[0],
            "district": geo.loc[geo.adm4_pcode == pcode, "district"].dropna().iloc[0] if pcode in tondo else None,
        }
        for pcode, place in BARANGAYS.items()
    },
    "problems": problems,
}
write_json(DERIVED / "census_2024_check.json", check)
print(f"match: {check['match']}; census people matched {check['census_people_matched']:,} of {census_total:,}")
for p in problems:
    print("  PROBLEM:", p)
if problems:
    sys.exit(1)
