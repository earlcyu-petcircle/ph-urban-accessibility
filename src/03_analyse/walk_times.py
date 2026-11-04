#!/usr/bin/env python3
"""
Walking distances along the OpenStreetMap network from every origin to the services.

The network is undirected and weighted by length. Origins (residential buildings) and services
join it at their nearest node by a straight hop, which counts as walking.

  nearest_by_node(...)   one multi-source search per category gives every node its distance to
                         the nearest service, hop included; an origin adds its own hop (M1, M4,
                         M5 and the sensitivity variants)
  counts_and_access(...) one search per service, cut at 20 minutes, gives every node the number
                         of services within 5, 10, 15 and 20 minutes (M2) and the E2SFCA access
                         score (M3); these are read at the origin's node, without its own hop

Run as a script, it writes:
  data/work/walk_times.parquet   one row per origin: people, hop, nearest metres per category,
                                 counts within each threshold, E2SFCA access, H3 cells
  data/work/nearest_nodes.npz    the node distance arrays of every layer variant, for
                                 sensitivity.py

Run after 02_build_tables.sh:  python src/03_analyse/walk_times.py
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import (
    CATEGORIES,
    E2SFCA_CATCHMENT_MIN,
    JEEPNEY_ROUTES_COUNT_AS_STOPS,
    OVERTURE_MIN_CONFIDENCE,
    ROOT,
    THRESHOLDS_MIN,
    UTM,
    WORK,
    metres,
    require,
)

TO_UTM = Transformer.from_crs("EPSG:4326", UTM, always_xy=True)
# The seven categories whose records come from Overture or OpenStreetMap by choice; open space
# (OpenStreetMap polygons) and transit (stops, stations and routes) are the same in every variant
POINT_CATEGORIES = tuple(c for c in CATEGORIES if c not in ("open_space", "transit"))
SCHOOLS = ("public_elementary", "public_high")


def xy(lon, lat):
    x, y = TO_UTM.transform(np.asarray(lon, dtype=float), np.asarray(lat, dtype=float))
    return np.column_stack([x, y])


class Network:
    """The walking network as a sparse graph, with a nearest-node lookup."""

    def __init__(self):
        require(WORK / "walk_edges.parquet", how="Run ./02_build_tables.sh first.")
        nodes = pd.read_parquet(WORK / "walk_nodes.parquet")
        edges = pd.read_parquet(WORK / "walk_edges.parquet")
        idx = pd.Series(np.arange(len(nodes)), index=nodes.node_id.values)
        self.u, self.v = idx[edges.u].values, idx[edges.v].values
        self.w = edges.length_m.values.astype(float)
        self.n = len(nodes)
        self.node_id = nodes.node_id.values
        self.index_of = idx
        self.xy = xy(nodes.lon, nodes.lat)
        self.tree = cKDTree(self.xy)
        self.graph = coo_matrix(
            (np.r_[self.w, self.w], (np.r_[self.u, self.v], np.r_[self.v, self.u])), shape=(self.n, self.n)
        ).tocsr()

    def snap(self, lon, lat):
        """Nearest node of each point, and the straight hop to it in metres."""
        hop, node = self.tree.query(xy(lon, lat))
        return node, hop

    def nearest(self, nodes, hops):
        """Every node's distance to the nearest of the given source nodes (each with its hop)."""
        src = pd.DataFrame({"i": nodes, "o": hops}).groupby("i").o.min()
        # A virtual node n joined to every source; weights must be above 0 to count as edges
        rows = np.concatenate([self.u, self.v, np.full(len(src), self.n)])
        cols = np.concatenate([self.v, self.u, src.index.values])
        vals = np.concatenate([self.w, self.w, src.values + 1e-3])
        m = coo_matrix((vals, (rows, cols)), shape=(self.n + 1, self.n + 1)).tocsr()
        return dijkstra(m, directed=True, indices=self.n)[: self.n] - 1e-3

    def within(self, sources, limit):
        """Distances (sources x nodes) from each source node, cut at `limit` metres."""
        return dijkstra(self.graph, directed=False, indices=sources, limit=limit)


# ---------------------------------------------------------------------------
# The service layers
# ---------------------------------------------------------------------------
def load_services():
    svc = pd.read_parquet(WORK / "services.parquet")
    groups = svc.groupby("dup_group").source.agg(set)
    svc["registry_group"] = svc.dup_group.map(lambda g: "deped" in groups[g])
    return svc


def layer_points(svc, access, routes, variant="merged", confidence=OVERTURE_MIN_CONFIDENCE, routes_as_stops=None):
    """The points of every category in one layer variant, as {category: (lon, lat)}.

    variant: merged (the default layer's sources), overture or osm (check 07);
    confidence: the Overture threshold (check 08); routes_as_stops: the jeepney rule (check 10).
    For the nearest service duplicates do not matter, so every record that qualifies counts."""
    if routes_as_stops is None:
        routes_as_stops = JEEPNEY_ROUTES_COUNT_AS_STOPS
    keep = svc.source.eq("osm") | svc.source.eq("deped") | (svc.confidence >= confidence)
    if variant == "overture":
        keep &= svc.source.eq("overture")
    elif variant == "osm":
        keep &= svc.source.eq("osm")
    # In the merged layer DepEd defines the public-school categories; the single-source
    # variants use each source's own public schools
    keep &= ~svc.category.isin(SCHOOLS) | (svc.registry_group if variant == "merged" else True)
    out = {}
    for c in POINT_CATEGORIES:
        d = svc[keep & svc.category.eq(c)]
        out[c] = (d.lon.values, d.lat.values)
    open_ids = svc.service_id[svc.category.eq("open_space") & svc.in_default]
    a = access[access.service_id.isin(open_ids)]
    out["open_space"] = (a.lon.values, a.lat.values)
    t = svc[svc.category.eq("transit") & (svc.source.eq("osm") | (svc.confidence >= OVERTURE_MIN_CONFIDENCE))]
    lon, lat = [t.lon.values], [t.lat.values]
    if routes_as_stops:
        lon.append(routes.lon.values)
        lat.append(routes.lat.values)
    out["transit"] = (np.concatenate(lon), np.concatenate(lat))
    return out


def transit_points(svc, routes, routes_as_stops=None):
    """M5's two kinds of transit: bus and jeepney (stops, terminals and, by the rule, routes) and rail."""
    if routes_as_stops is None:
        routes_as_stops = JEEPNEY_ROUTES_COUNT_AS_STOPS
    t = svc[svc.category.eq("transit") & (svc.source.eq("osm") | (svc.confidence >= OVERTURE_MIN_CONFIDENCE))]
    rail = t[t.kind.eq("rail_station")]
    road = t[~t.kind.eq("rail_station")]
    lon, lat = [road.lon.values], [road.lat.values]
    if routes_as_stops:
        lon.append(routes.lon.values)
        lat.append(routes.lat.values)
    return {"bus_jeepney": (np.concatenate(lon), np.concatenate(lat)), "rail": (rail.lon.values, rail.lat.values)}


def nearest_by_node(net, points):
    """{name: node distance array (float32)} for {name: (lon, lat)}."""
    out = {}
    for name, (lon, lat) in points.items():
        node, hop = net.snap(lon, lat)
        out[name] = net.nearest(node, hop).astype("float32")
    return out


# ---------------------------------------------------------------------------
# M2 counts and M3 E2SFCA, one search per service
# ---------------------------------------------------------------------------
def gaussian(d, d0):
    """The Gaussian distance decay of E2SFCA: 1 at the door, 0 at the catchment edge d0."""
    edge = np.exp(-0.5)
    return np.where(d <= d0, (np.exp(-0.5 * (d / d0) ** 2) - edge) / (1 - edge), 0.0)


def counts_and_access(net, svc, access, pop_node, batch=64):
    """Per category: node counts of default-layer services within each threshold, and the
    E2SFCA access score (supply per resident within reach, Gaussian decay inside the catchment).

    Supply is 1 per service, or a school's DepEd enrolment. Transit has no supply, so it gets
    counts only. A park is reached at its nearest access point, a rail station at its nearest
    platform; other services at their own point."""
    limits = [metres(m) for m in THRESHOLDS_MIN]
    d0 = metres(E2SFCA_CATCHMENT_MIN)
    counts, scores = {}, {}
    for c in CATEGORIES:
        d = svc[svc.category.eq(c) & svc.in_default]
        cnt = np.zeros((len(limits), net.n), dtype=np.int32)
        acc = np.zeros(net.n)
        sources = []  # (node indices, hops, supply)
        if c == "open_space":
            a = access[access.service_id.isin(d.service_id)]
            for _, g in a.groupby("service_id"):
                node, hop = net.snap(g.lon, g.lat)
                sources.append((node, hop, 1.0))
        elif c == "transit":
            members = svc[svc.dup_group.isin(d.dup_group) & svc.category.eq(c)]
            for _, g in members.groupby("dup_group"):
                node, hop = net.snap(g.lon, g.lat)
                sources.append((node, hop, 1.0))
        else:
            node, hop = net.snap(d.lon, d.lat)
            supply = d.group_capacity.fillna(1.0).values if c in SCHOOLS else np.ones(len(d))
            sources = [(np.array([i]), np.array([h]), s) for i, h, s in zip(node, hop, supply, strict=True)]
        single = [k for k, s in enumerate(sources) if len(s[0]) == 1]
        multi = [k for k, s in enumerate(sources) if len(s[0]) > 1]
        for start in range(0, len(single), batch):
            ks = single[start : start + batch]
            dist = net.within(np.array([sources[k][0][0] for k in ks]), limits[-1])
            dist += np.array([sources[k][1][0] for k in ks])[:, None]
            _accumulate(dist, [sources[k][2] for k in ks], cnt, acc, limits, d0, pop_node)
        for k in multi:
            node, hop, supply = sources[k]
            dist = net.within(node, limits[-1]) + hop[:, None]
            _accumulate(dist.min(axis=0)[None, :], [supply], cnt, acc, limits, d0, pop_node)
        counts[c] = cnt
        if c != "transit":
            scores[c] = acc
    return counts, scores


def _accumulate(dist, supply, cnt, acc, limits, d0, pop_node):
    rows, cols = np.nonzero(np.isfinite(dist))
    dd = dist[rows, cols]
    for j, lim in enumerate(limits):
        ok = dd <= lim
        cnt[j] += np.bincount(cols[ok], minlength=cnt.shape[1]).astype(np.int32)
    w = gaussian(dd, d0)
    demand = np.bincount(rows, weights=w * pop_node[cols], minlength=dist.shape[0])
    ratio = np.divide(np.asarray(supply, dtype=float), demand, out=np.zeros(len(demand)), where=demand > 0)
    acc += np.bincount(cols, weights=w * ratio[rows], minlength=acc.shape[0])


# ---------------------------------------------------------------------------
# The script: every origin's distances, counts and access
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    net = Network()
    print(f"network: {net.n:,} nodes ({time.time() - t0:.0f}s)")
    origins = pd.read_parquet(WORK / "origins.parquet")
    svc = load_services()
    access = pd.read_parquet(WORK / "open_space_access.parquet")
    routes = pd.read_parquet(WORK / "transit_routes.parquet").drop_duplicates("node_id")

    o_node, o_hop = net.snap(origins.lon, origins.lat)
    out = origins[["origin_id", "pcode", "people", "people_ghs", "h3_10", "h3_9", "wp_cell", "lon", "lat"]].copy()
    out["node"], out["hop_m"] = o_node.astype(np.int32), o_hop.astype("float32")
    print(
        f"origins: {len(out):,}; hop to the network median {np.median(o_hop):.0f} m, "
        f"P95 {np.percentile(o_hop, 95):.0f} m"
    )

    # Nearest service, for the default layer and every variant the checks need
    variants = {
        "merged": layer_points(svc, access, routes),
        "overture": layer_points(svc, access, routes, variant="overture"),
        "osm": layer_points(svc, access, routes, variant="osm"),
        "conf_0.3": layer_points(svc, access, routes, confidence=0.3),
        "conf_0.7": layer_points(svc, access, routes, confidence=0.7),
    }
    arrays = {}
    for name, pts in variants.items():
        cats = CATEGORIES if name == "merged" else POINT_CATEGORIES
        for c, arr in nearest_by_node(net, {c: pts[c] for c in cats}).items():
            arrays[f"{name}:{c}"] = arr
        print(f"  nearest, {name} layer ({time.time() - t0:.0f}s)")
    # Food without convenience stores: the paper reports food access both ways (section 8)
    food = svc[svc.category.eq("food_retail") & svc.in_default & ~svc.kind.eq("convenience")]
    arrays["merged:food_retail_no_convenience"] = nearest_by_node(net, {"x": (food.lon.values, food.lat.values)})["x"]
    stops_only = layer_points(svc, access, routes, routes_as_stops=False)
    arrays["stops_only:transit"] = nearest_by_node(net, {"transit": stops_only["transit"]})["transit"]
    for name, pts in transit_points(svc, routes).items():
        arrays[f"m5:{name}"] = nearest_by_node(net, {name: pts})[name]
    arrays["m5:bus_jeepney_stops_only"] = nearest_by_node(
        net, {"x": transit_points(svc, routes, routes_as_stops=False)["bus_jeepney"]}
    )["x"]
    np.savez_compressed(WORK / "nearest_nodes.npz", **arrays)

    for c in CATEGORIES:
        out[f"d_{c}"] = (arrays[f"merged:{c}"][o_node] + o_hop).astype("float32")
    out["d_food_retail_no_convenience"] = (arrays["merged:food_retail_no_convenience"][o_node] + o_hop).astype(
        "float32"
    )
    out["d_bus_jeepney"] = (arrays["m5:bus_jeepney"][o_node] + o_hop).astype("float32")
    out["d_rail"] = (arrays["m5:rail"][o_node] + o_hop).astype("float32")

    # Counts and E2SFCA, with demand from the census people placed at their nodes
    pop_node = np.bincount(o_node, weights=origins.people.values, minlength=net.n)
    counts, scores = counts_and_access(net, svc, access, pop_node)
    for c in CATEGORIES:
        for j, m in enumerate(THRESHOLDS_MIN):
            out[f"n_{c}_{m}"] = counts[c][j][o_node].astype(np.int16)
        if c in scores:
            out[f"a_{c}"] = (scores[c][o_node] * 10_000).astype("float32")  # per 10,000 residents
    print(f"  counts and E2SFCA ({time.time() - t0:.0f}s)")
    out.to_parquet(WORK / "walk_times.parquet", index=False)
    print(f"wrote {(WORK / 'walk_times.parquet').relative_to(ROOT)} and nearest_nodes.npz ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
