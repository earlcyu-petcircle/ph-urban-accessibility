"""
The five measures, summarised over residents (every statistic is weighted by people):

  M1 nearest walk     minutes to the nearest service of each category: median, P10, P90, the
                      P90/P10 ratio and the share within the 10-minute minimum
  M2 choice           services of each category within 5, 10 and 15 minutes: median and mean
  M3 crowding         E2SFCA access per 10,000 residents: median and mean
  M4 coverage         how many of the nine categories are within 15 minutes: mean, and the share
                      of residents with each count
  M5 transit          shares within 500 m of a bus or jeepney stop or route, within 1 km of an
                      LRT or MRT station, and within either (UN SDG 11.2.1)

and the context: each barangay's median resident placed among all Metro Manila residents, among
residents of barangays of similar density, and beside its neighbours.

Jollibee (NOT_IN_SCORE in src/shared/common.py) is a service the site shows beside the nine:
`barangay_table` and `service_stats` give it the same M1, M2 and M3 answers when asked, and
coverage (M4), the 15-minute score and its rank count only the nine.

Used by the notebooks; reads data/work/walk_times.parquet (walk_times.py).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import (
    BARANGAYS,
    CATEGORIES,
    COVERAGE_MIN,
    DERIVED,
    NOT_IN_SCORE,
    SUFFICIENCY_MIN,
    TRANSIT_HIGH_CAPACITY_M,
    TRANSIT_LOW_CAPACITY_M,
    WALK_SPEED_KMH,
    WORK,
    metres,
    require,
)

STUDY = [v["name"] for v in BARANGAYS.values()]
LABEL = {
    "food_retail": "Food retail",
    "palengke": "Palengke",
    "pharmacy": "Pharmacy",
    "primary_care": "Primary care",
    "hospital": "Hospital",
    "public_elementary": "Public elementary",
    "public_high": "Public high",
    "open_space": "Open space",
    "transit": "Transit",
    "jollibee": "Jollibee",
    "food_retail_no_convenience": "Food retail without convenience stores",
}
M3_CATEGORIES = tuple(c for c in CATEGORIES if c != "transit")
# Every service with a supply to share (all but transit), counted in the score or not
CROWDING = M3_CATEGORIES + NOT_IN_SCORE


def minutes(m, speed_kmh=WALK_SPEED_KMH):
    return m / (speed_kmh * 1000 / 60)


def wquantile(x, w, q):
    """People-weighted quantile(s) q of x (the value below which a share q of people fall)."""
    x, w = np.asarray(x, dtype=float), np.asarray(w, dtype=float)
    ok = np.isfinite(x) & (w > 0)
    x, w = x[ok], w[ok]
    order = np.argsort(x)
    x, cw = x[order], np.cumsum(w[order])
    return np.interp(np.atleast_1d(q) * cw[-1], cw - w[order] / 2, x)


def wmedian(x, w, step=False):
    """People-weighted median; with step=True the value at which half the people are reached
    (for counts, so the median is a whole number)."""
    if not step:
        return float(wquantile(x, w, 0.5)[0])
    x, w = np.asarray(x, dtype=float), np.asarray(w, dtype=float)
    order = np.argsort(x)
    cw = np.cumsum(w[order])
    return float(x[order][np.searchsorted(cw, 0.5 * cw[-1])])


def wmean(x, w):
    return float(np.average(np.asarray(x, dtype=float), weights=w))


def load():
    require(WORK / "walk_times.parquet", how="Run src/03_analyse/walk_times.py first.")
    w = pd.read_parquet(WORK / "walk_times.parquet")
    b = pd.read_csv(DERIVED / "barangays.csv", keep_default_na=False)
    w = w.merge(b[["pcode", "barangay", "city", "tondo_district", "study", "people_per_km2"]], on="pcode")
    return w, b


def areas(w):
    """The study barangays, their neighbours and Metro Manila, as {name: row mask}."""
    out = {name: w.study.eq(name) for name in STUDY}
    out["Tondo, other 258 barangays"] = w.tondo_district & w.study.eq("")
    out["Quezon City, other barangays"] = w.city.eq("Quezon City") & w.study.eq("")
    out["City of Pasig, other barangays"] = w.city.eq("City of Pasig") & w.study.eq("")
    out["Metro Manila"] = pd.Series(True, index=w.index)
    return out


def coverage(w, minutes_=COVERAGE_MIN, speed_kmh=WALK_SPEED_KMH, prefix="d_"):
    """M4: how many of the nine categories each origin has within `minutes_`."""
    lim = metres(minutes_, speed_kmh)
    return sum((w[f"{prefix}{c}"] <= lim).astype(int) for c in CATEGORIES)


def transit_shares(d_bus, d_rail, people):
    low = d_bus <= TRANSIT_LOW_CAPACITY_M
    high = d_rail <= TRANSIT_HIGH_CAPACITY_M
    return {
        "share_within_500m_bus_jeepney": wmean(low, people),
        "share_within_1km_rail": wmean(high, people),
        "share_convenient": wmean(low | high, people),
    }


def measures_table(w):
    """Every measure for every area, in long form: area, measure, category, stat, value."""
    rows = []

    def add(area, measure, category, stat, value):
        rows.append({"area": area, "measure": measure, "category": category, "stat": stat, "value": float(value)})

    for area, mask in areas(w).items():
        d = w[mask]
        p = d.people.values
        add(area, "people", "", "people", p.sum())
        for c in CATEGORIES:
            for (measure, stat), v in service_stats(d, c).items():
                add(area, measure, c, stat, v)
        mins = minutes(d.d_food_retail_no_convenience.values)
        p10, p50, p90 = wquantile(mins, p, [0.1, 0.5, 0.9])
        for stat, v in (("median_min", p50), ("p10_min", p10), ("p90_min", p90)):
            add(area, "M1", "food_retail_no_convenience", stat, v)
        add(area, "M1", "food_retail_no_convenience", "share_within_10min", wmean(mins <= SUFFICIENCY_MIN, p))
        cov = coverage(d)
        add(area, "M4", "", "mean_categories_within_15min", wmean(cov, p))
        add(area, "M4", "", "median_categories_within_15min", wmedian(cov, p, step=True))
        for k in range(10):
            add(area, "M4", "", f"share_with_{k}", wmean(cov == k, p))
        for stat, v in transit_shares(d.d_bus_jeepney, d.d_rail, p).items():
            add(area, "M5", "", stat, v)
    return pd.DataFrame(rows)


def service_stats(d, c):
    """M1, M2 and (but for transit) M3 for one service over the residents in `d`, as
    {(measure, stat): value}: the rows measures_table writes for each category, and Metro
    Manila's figures for a service outside the score."""
    p = d.people.values
    mins = minutes(d[f"d_{c}"].values)
    p10, p50, p90 = wquantile(mins, p, [0.1, 0.5, 0.9])
    out = {
        ("M1", "median_min"): p50,
        ("M1", "p10_min"): p10,
        ("M1", "p90_min"): p90,
        ("M1", "p90_p10_ratio"): p90 / max(p10, 0.1),
        ("M1", "share_within_10min"): wmean(mins <= SUFFICIENCY_MIN, p),
    }
    for m in (5, 10, 15):
        out["M2", f"median_within_{m}min"] = wmedian(d[f"n_{c}_{m}"], p, step=True)
        out["M2", f"mean_within_{m}min"] = wmean(d[f"n_{c}_{m}"], p)
    if c in CROWDING:
        out["M3", "median_per_10k"] = wmedian(d[f"a_{c}"], p)
        out["M3", "mean_per_10k"] = wmean(d[f"a_{c}"], p)
    return out


def context_table(w):
    """Each study barangay's median resident as a percentile of Metro Manila residents.

    `share_metro_worse` is the share of all Metro Manila residents with worse access (a longer
    walk, or fewer categories); `share_similar_density_worse` the same among residents of
    barangays in the same people-weighted density tenth."""
    w = w.copy()
    dens = w.drop_duplicates("pcode")[["pcode", "people_per_km2"]]
    pop = w.groupby("pcode").people.sum()
    dens = dens.assign(pop=dens.pcode.map(pop)).sort_values("people_per_km2")
    dens["tenth"] = np.minimum((dens["pop"].cumsum() / dens["pop"].sum() * 10).astype(int), 9)
    w["density_tenth"] = w.pcode.map(dens.set_index("pcode").tenth)
    w["m4"] = coverage(w)
    rows = []
    for name in STUDY:
        d = w[w.study.eq(name)]
        tenth = int(d.density_tenth.iloc[0])
        similar = w[w.density_tenth.eq(tenth)]
        for metric, col, better_low in [(f"M1 {c}", f"d_{c}", True) for c in CATEGORIES] + [("M4", "m4", False)]:
            med = wmedian(d[col], d.people, step=not better_low)

            def worse(frame, med=med, col=col, better_low=better_low):
                x = frame[col]
                return wmean(x > med if better_low else x < med, frame.people)

            rows.append(
                {
                    "barangay": name,
                    "metric": metric,
                    "median": minutes(med) if better_low else med,
                    "share_metro_worse": worse(w),
                    "density_tenth": tenth + 1,
                    "share_similar_density_worse": worse(similar),
                }
            )
    return pd.DataFrame(rows)


def group_median(values, people, keys):
    """People-weighted median of `values` within each key (the value at which half the people are reached)."""
    d = pd.DataFrame({"k": keys, "v": values, "p": people}).sort_values(["k", "v"])
    d["cum"] = d.groupby("k").p.cumsum()
    d["half"] = d.groupby("k").p.transform("sum") / 2
    return d[d.cum >= d.half].drop_duplicates("k").set_index("k").v


def group_mean(values, people, keys):
    d = pd.DataFrame({"k": keys, "v": np.asarray(values, dtype=float) * people, "p": people}).groupby("k").sum()
    return d.v / d.p


def group_quantile(values, people, keys, q):
    """People-weighted quantile q of `values` within each key, interpolated as in `wquantile`."""
    d = pd.DataFrame({"k": keys, "v": np.asarray(values, dtype=float), "p": np.asarray(people, dtype=float)})
    return d.groupby("k").apply(lambda g: float(wquantile(g.v, g.p, q)[0]), include_groups=False)


def barangay_table(w, services=CATEGORIES):
    """The same measures for every barangay with people, for the comparison site, which answers
    the five research questions for any pick: the median resident's walk to each of `services`
    (the nine, and for the site Jollibee too) (M1),
    the P10 and P90 walks (the spread inside the barangay) and the share within the 10-minute
    minimum; the median resident's count within 5, 10 and 15 minutes (M2); the share of Metro
    Manila residents with a longer walk than that median; E2SFCA access against the Metro
    Manila mean (M3); mean categories within 15 minutes (M4) as a 0-100 score, the share with
    all nine and the share of Metro Manila residents with fewer than the median resident; and
    the transit shares (M5). The score and its rank count only the nine, whatever `services`
    holds. One row per barangay, wide."""
    w = w[w.people > 0]
    keys, p = w.pcode.values, w.people.values
    out = pd.DataFrame({"people": w.groupby("pcode").people.sum()})
    for c in services:
        d = w[f"d_{c}"].values
        med = group_median(d, p, keys)
        out[f"min_{c}"] = minutes(med)
        out[f"p10_min_{c}"] = minutes(group_quantile(d, p, keys, 0.1))
        out[f"p90_min_{c}"] = minutes(group_quantile(d, p, keys, 0.9))
        out[f"within10_{c}"] = group_mean(minutes(d) <= SUFFICIENCY_MIN, p, keys)
        for m in (5, 10, 15):
            out[f"n{m}_{c}"] = group_median(w[f"n_{c}_{m}"].values, p, keys)
        order = np.argsort(d)
        xs, cw = d[order], np.cumsum(p[order])
        out[f"metro_longer_{c}"] = (
            1 - np.r_[0, cw][np.searchsorted(xs, med.reindex(out.index).values, "right")] / cw[-1]
        )
        if c in CROWDING:
            out[f"m3_index_{c}"] = group_mean(w[f"a_{c}"].values, p, keys) / wmean(w[f"a_{c}"], p)
    cov = coverage(w).values
    out["m4_mean"] = group_mean(cov, p, keys)
    out["score"] = out.m4_mean / len(CATEGORIES) * 100
    out["share_all_nine"] = group_mean(cov == len(CATEGORIES), p, keys)
    cov_med = group_median(cov, p, keys)
    order = np.argsort(cov)
    xs, cw = cov[order], np.cumsum(p[order])
    out["m4_metro_fewer"] = np.r_[0, cw][np.searchsorted(xs, cov_med.reindex(out.index).values, "left")] / cw[-1]
    out["share_bus_jeepney_500m"] = group_mean(w.d_bus_jeepney.values <= TRANSIT_LOW_CAPACITY_M, p, keys)
    out["share_rail_1km"] = group_mean(w.d_rail.values <= TRANSIT_HIGH_CAPACITY_M, p, keys)
    out["share_convenient"] = group_mean(
        (w.d_bus_jeepney.values <= TRANSIT_LOW_CAPACITY_M) | (w.d_rail.values <= TRANSIT_HIGH_CAPACITY_M), p, keys
    )
    out["score_rank"] = out.score.rank(ascending=False, method="min").astype(int)
    return out.reset_index()
