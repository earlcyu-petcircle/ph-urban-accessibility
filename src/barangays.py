#!/usr/bin/env python3
"""
Step 2: the neighbourhood unit. Joins the 1,712 Metro Manila barangay polygons
(PSA / NAMRIA COD-AB v03) to the PSA 2020 census population of each barangay.

The two files code barangays differently inside the City of Manila (the census
uses the district-based PSGC, the boundaries a city-wide sequence), so the join
is on city + barangay name, with "(Pob.)"-style suffixes stripped. Every one of
the 1,710 census barangays matches; the two extra polygons are Manila North
Cemetery and the disputed Tutuban Mall lot, which have no census population.
"""
import re

import geopandas as gpd
import pandas as pd

from common import BOUNDARIES, RAW, WORK

# City of Manila districts, from the 4th-5th digits of the old 9-digit PSGC (PH1339DD...).
MANILA_DISTRICTS = {
    "01": "Tondo", "02": "Binondo", "03": "Quiapo", "04": "San Nicolas", "05": "Santa Cruz",
    "06": "Sampaloc", "07": "San Miguel", "08": "Ermita", "09": "Intramuros", "10": "Malate",
    "11": "Paco", "12": "Pandacan", "13": "Port Area", "14": "Santa Ana",
}


def city_key(s):
    return re.sub(r"^city of |\s*city$", "", s.lower()).strip()


def name_key(s):
    s = re.sub(r"\(.*?\)", "", s.lower().replace("ñ", "n")).replace("blvd.", "boulevard")
    return re.sub(r"[^a-z0-9]", "", s)


geo = gpd.read_file(BOUNDARIES, layer="phl_admin4", where="adm1_pcode = 'PH13'")
geo = geo[["adm4_pcode", "adm4_name", "adm3_name", "version", "valid_on", "geometry"]]

census = pd.read_excel(RAW / "phl_census2020_brgy.xlsx", sheet_name="2020 CPH", dtype=str)
census.columns = [c.replace("\n", " ") for c in census.columns]
census = census[census["Reg_Code"] == "PH130000000"].copy()
census["pop2020"] = census["2020 Census Popn"].astype(int)
census["district"] = census["Bgy_Code"].str[6:8].map(MANILA_DISTRICTS).where(
    census["Mun_City"] == "City of Manila")

geo["key"] = geo.adm3_name.map(city_key) + "|" + geo.adm4_name.map(name_key)
census["key"] = census.Mun_City.map(city_key) + "|" + census.Barangay.map(name_key)
assert not geo.key.duplicated().any() and not census.key.duplicated().any()

b = geo.merge(census[["key", "pop2020", "district", "Urban / Rural (based on 2020 CPH)"]],
              on="key", how="left", validate="1:1")
unmatched = set(census.key) - set(b.key)
assert not unmatched, f"census barangays without a polygon: {unmatched}"
assert b.pop2020.sum() == census.pop2020.sum()

b = b.rename(columns={"adm4_pcode": "pcode", "adm4_name": "barangay", "adm3_name": "city"})
b["pop2020"] = b.pop2020.fillna(0).astype(int)
b["area_km2"] = b.to_crs("EPSG:32651").area / 1e6   # UTM 51N, metres
b["density_km2"] = b.pop2020 / b.area_km2

# The three places lived, as barangay outlines only.
b["place_lived"] = None
b.loc[b.district.eq("Tondo"), "place_lived"] = "tondo"
b.loc[b.city.eq("Quezon City") & b.barangay.eq("Loyola Heights"), "place_lived"] = "loyola"
b.loc[b.city.eq("City of Pasig") & b.barangay.eq("Oranbo"), "place_lived"] = "oranbo"
assert b.place_lived.value_counts().to_dict().keys() == {"tondo", "loyola", "oranbo"}

b = b[["pcode", "barangay", "city", "district", "pop2020", "area_km2", "density_km2",
       "place_lived", "version", "valid_on", "geometry"]].sort_values("pcode").reset_index(drop=True)
b.to_parquet(WORK / "barangays.parquet")
print(f"wrote data/work/barangays.parquet  |  {len(b)} barangays, {b.pop2020.sum():,} people (PSA 2020), "
      f"boundaries {b.version.iloc[0]} valid from {b.valid_on.iloc[0]:%Y-%m-%d}; "
      f"Tondo district = {b.place_lived.eq('tondo').sum()} barangays")
