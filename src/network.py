#!/usr/bin/env python3
"""
Step 4: walking distance from every lived-in building to the nearest service of
each type, along the OpenStreetMap walking network.

For each service, one multi-source Dijkstra run from all its locations at once
gives the network distance from every network node to the nearest one. Buildings
and services join the network at their nearest node; the straight-line hop to
that node is added on both ends. Writes data/work/origin_dist.parquet.
"""
import numpy as np
import pandas as pd
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

from common import MIN_CONFIDENCE, WORK, connect

LAT0 = 14.6  # metres per degree at Metro Manila's latitude, for snapping only
MX, MY = 111_320 * np.cos(np.radians(LAT0)), 110_574


def xy(lon, lat):
    return np.column_stack([np.asarray(lon) * MX, np.asarray(lat) * MY])


con = connect()
edges = con.sql(f"SELECT u, v, length_m FROM '{WORK}/walk_edges.parquet' WHERE u <> v").df()
nodes = con.sql(f"""SELECT id, lon, lat FROM '{WORK}/osm_nodes.parquet'
                    WHERE id IN (SELECT u FROM '{WORK}/walk_edges.parquet'
                                 UNION SELECT v FROM '{WORK}/walk_edges.parquet')""").df()

# Graph on the largest connected piece of the network, so no one snaps to an island.
idx = pd.Series(np.arange(len(nodes)), index=nodes.id.values)
u, v = idx[edges.u].values, idx[edges.v].values
g = coo_matrix((edges.length_m.values, (u, v)), shape=(len(nodes),) * 2).tocsr()
_, comp = connected_components(g, directed=False)
keep = comp == np.bincount(comp).argmax()
nodes = nodes[keep].reset_index(drop=True)
idx = pd.Series(np.arange(len(nodes)), index=nodes.id.values)
e = edges[edges.u.isin(idx.index) & edges.v.isin(idx.index)]
n = len(nodes)
u, v, w = idx[e.u].values, idx[e.v].values, e.length_m.values
tree = cKDTree(xy(nodes.lon, nodes.lat))
print(f"walking network: {n:,} nodes, {len(e):,} segments, {w.sum() / 1000:,.0f} km "
      f"(largest connected piece, {keep.mean():.1%} of nodes)")


def snap(lon, lat):
    d, i = tree.query(xy(lon, lat))
    return i, d


def distances(node_i, offset):
    """Network distance from every node to the nearest source, entering at node_i with offset metres."""
    src = pd.DataFrame({"i": node_i, "o": offset}).groupby("i").o.min()
    # A virtual node n joined to every source; edge weights must be > 0 to count as edges.
    rows = np.concatenate([u, v, np.full(len(src), n)])
    cols = np.concatenate([v, u, src.index.values])
    vals = np.concatenate([w, w, src.values + 1e-3])
    m = coo_matrix((vals, (rows, cols)), shape=(n + 1, n + 1)).tocsr()
    return dijkstra(m, directed=True, indices=n)[:n]


# ---- service locations ----
places_all = con.sql(f"""SELECT service, is_palengke, confidence, lon, lat FROM '{WORK}/overture_places.parquet'
                         WHERE coalesce(operating_status, 'open') = 'open'""").df()
places = places_all[places_all.confidence >= MIN_CONFIDENCE]
osm = con.sql(f"""SELECT service, kind, lon, lat, node_id FROM '{WORK}/osm_services.parquet'
                  WHERE kind <> 'crosscheck'""").df()
parks = con.sql(f"SELECT wkb FROM '{WORK}/overture_parks.parquet'").df()

# Park entrances: points every 25 m round each park's edge.
edge_pts = shapely.get_coordinates(
    shapely.segmentize(shapely.boundary(shapely.from_wkb([bytes(b) for b in parks.wkb])), 25 / MX))
pts = {
    "grocery": pd.concat([places.query("service == 'grocery'")[["lon", "lat"]],
                          osm.query("kind == 'palengke'")[["lon", "lat"]]]),
    "palengke": pd.concat([places.query("is_palengke")[["lon", "lat"]],
                           osm.query("kind == 'palengke'")[["lon", "lat"]]]),
    "health": places.query("service == 'health'")[["lon", "lat"]],
    "schools": places.query("service == 'schools'")[["lon", "lat"]],
    "parks": pd.DataFrame(edge_pts, columns=["lon", "lat"]),
    "transit": pd.concat([places.query("service == 'transit'")[["lon", "lat"]],
                          osm.query("service == 'transit'")[["lon", "lat"]]]),
    "rail": osm.query("kind == 'rail'")[["lon", "lat"]],
    # Sensitivity checks (sql/q7_sensitivity.sql): every Overture record whatever its
    # confidence, and transit without the "board anywhere on a jeepney route" rule.
    "grocery_allconf": pd.concat([places_all.query("service == 'grocery'")[["lon", "lat"]],
                                  osm.query("kind == 'palengke'")[["lon", "lat"]]]),
    "health_allconf": places_all.query("service == 'health'")[["lon", "lat"]],
    "schools_allconf": places_all.query("service == 'schools'")[["lon", "lat"]],
    "transit_nojeepney": pd.concat([places.query("service == 'transit'")[["lon", "lat"]],
                                    osm.query("kind in ('rail', 'stop')")[["lon", "lat"]]]),
}

# ---- origins: lived-in buildings ----
o = con.sql(f"SELECT origin_id, pcode, pop, lon, lat FROM '{WORK}/origins.parquet'").df()
o_node, o_off = snap(o.lon, o.lat)
print(f"origins: {len(o):,}; hop to the network median {np.median(o_off):.0f} m, "
      f"95th percentile {np.percentile(o_off, 95):.0f} m")

out = o[["origin_id", "pcode", "pop"]].copy()
for name, p in pts.items():
    i, off = snap(p.lon, p.lat)
    d = distances(i, off)
    out[f"d_{name}"] = (d[o_node] + o_off).astype("float32")
    print(f"  {name:17s} {len(p):6,} locations; median resident {np.median(out[f'd_{name}']):5.0f} m")

out.to_parquet(WORK / "origin_dist.parquet", index=False)
print("wrote data/work/origin_dist.parquet")
