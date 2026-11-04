"""
The validation audits of docs/paper.md (section 4.6).

  registry_match()           the share of DepEd public schools found in the open sources, per
                             area (from data/derived/service_quality.csv); there is no DOH
                             registry, and Healthsites.io is used only when HDX lets it download
  service_audit_sample(...)  a random 30 services within a 15-minute walk of each barangay's
                             residents, with a street-imagery link and blank columns for the
                             found-and-open check
  walk_audit_routes(...)     20 walking routes per barangay, from street points inside it (or
                             within 200 m of a barangay too small to hold 20) to the nearest
                             service of each category in turn, with links and blank columns for
                             sidewalk, crossings, shade, obstruction and sari-sari stores seen

The imagery itself is judged by a person, not by this code: the two samples are the audit's
fixed, reproducible worksheets (seed 2026). Routes start at street nodes, never at a building.
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import BARANGAYS, CATEGORIES, DERIVED, HEALTHSITES_CSV, UTM, metres, read_ncr_barangays
from measures import minutes

SEED = 2026
SERVICE_SAMPLE = 30
ROUTES = 20


def imagery_link(lon, lat):
    return f"https://www.mapillary.com/app/?lat={lat:.6f}&lng={lon:.6f}&z=18"


def registry_match():
    q = pd.read_csv(DERIVED / "service_quality.csv")
    r = q[q.measure.eq("deped_registry_found")].rename(columns={"value": "found", "of": "deped_schools"})
    r["share_found"] = r.found / r.deped_schools
    r.attrs["healthsites"] = HEALTHSITES_CSV.exists()
    return r[["area", "category", "found", "deped_schools", "share_found"]].reset_index(drop=True)


def service_audit_sample(w, net, svc):
    """A random 30 default-layer services within 15 minutes' walk of each barangay's residents."""
    rng = np.random.default_rng(SEED)
    d_svc = svc[svc.in_default].copy()
    d_svc["node"], d_svc["hop"] = net.snap(d_svc.lon, d_svc.lat)
    rows = []
    for pcode, place in BARANGAYS.items():
        nodes = np.unique(w.node[w.pcode.eq(pcode)].values)
        reach = net.nearest(nodes, np.zeros(len(nodes)))
        near = d_svc[(reach[d_svc.node.values] + d_svc.hop.values) <= metres(15)]
        pick = near.iloc[np.sort(rng.choice(len(near), size=min(SERVICE_SAMPLE, len(near)), replace=False))]
        for _, s in pick.iterrows():
            rows.append(
                {
                    "barangay": place["name"],
                    "category": s.category,
                    "kind": s.kind,
                    "source": s.sources_in_group,
                    "name": s["name"],
                    "lon": round(s.lon, 6),
                    "lat": round(s.lat, 6),
                    "walk_min_from_nearest_resident": round(minutes(reach[s.node] + s.hop), 1),
                    "imagery": imagery_link(s.lon, s.lat),
                    "found": "",
                    "open": "",
                    "notes": "",
                }
            )
    return pd.DataFrame(rows)


def walk_audit_routes(net, svc):
    """20 routes per barangay from street points inside it to the nearest service of each category."""
    rng = np.random.default_rng(SEED)
    geo = read_ncr_barangays(columns=["adm4_pcode"]).set_index("adm4_pcode").to_crs(UTM)
    d_svc = svc[svc.in_default & ~svc.category.eq("open_space")].copy()
    d_svc["node"], _ = net.snap(d_svc.lon, d_svc.lat)
    rows = []
    for pcode, place in BARANGAYS.items():
        poly = geo.geometry[pcode]
        inside = np.flatnonzero(shapely.contains_xy(poly, net.xy[:, 0], net.xy[:, 1]))
        if len(inside) < ROUTES:
            inside = np.flatnonzero(shapely.contains_xy(poly.buffer(200), net.xy[:, 0], net.xy[:, 1]))
        starts = rng.choice(inside, size=ROUTES, replace=False)
        for k, start in enumerate(starts):
            category = CATEGORIES[k % len(CATEGORIES)]
            if category == "open_space":
                category = "public_elementary" if k % 2 else "palengke"
            dist, pred = dijkstra(
                net.graph, directed=False, indices=int(start), return_predecessors=True, limit=metres(30)
            )
            targets = d_svc[d_svc.category.eq(category)]
            reachable = targets[np.isfinite(dist[targets.node.values])]
            if reachable.empty:
                continue
            end = reachable.iloc[np.argmin(dist[reachable.node.values])]
            path, node = [], int(end.node)
            while node >= 0:
                path.append(node)
                node = pred[node] if node != start else -9999
            path = path if len(path) > 1 else path * 2  # a service at the start point
            line = gpd.GeoSeries([shapely.LineString(net.xy[path[::-1]])], crs=UTM).to_crs(4326).iloc[0]
            s_lon, s_lat = line.coords[0]
            rows.append(
                {
                    "barangay": place["name"],
                    "route": k + 1,
                    "to_category": category,
                    "to_name": end["name"],
                    "length_m": round(float(dist[end.node])),
                    "walk_min": round(minutes(dist[end.node]), 1),
                    "start_imagery": imagery_link(s_lon, s_lat),
                    "end_imagery": imagery_link(end.lon, end.lat),
                    "route_wkt": shapely.to_wkt(line, rounding_precision=6),
                    "sidewalk": "",
                    "crossings": "",
                    "shade": "",
                    "obstruction": "",
                    "sari_sari_seen": "",
                }
            )
    return pd.DataFrame(rows)
