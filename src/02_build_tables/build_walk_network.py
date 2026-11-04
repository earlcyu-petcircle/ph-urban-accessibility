#!/usr/bin/env python3
"""
Build the OpenStreetMap walking network for Metro Manila plus the fringe (STUDY_BOX in
src/shared/common.py): every way a pedestrian may use, walkable in both directions, kept to
its largest connected component; expressways out, footbridges and stairs in.

The way filter copies OSMnx's "walk" network type: any highway a person may walk on, so trunk
roads such as EDSA (which have sidewalks) stay in, while expressways (motorway and its links),
cycleways, bus guideways, platforms, private ways, ways marked foot=no and anything abandoned,
proposed or under construction are dropped. Each way is cut into its node-to-node segments;
a segment is kept when both ends are in the box.

  data/work/walk_nodes.parquet   node_id, lon, lat
  data/work/walk_edges.parquet   u, v (node ids), length_m, way_id, highway
  data/work/walk_stats.json      size, connectivity and the extract's snapshot time

Run after build_services.py:  python src/02_build_tables/build_walk_network.py
"""

import sys
from array import array
from pathlib import Path

import numpy as np
import osmium
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

from common import OSM_PBF, ROOT, STUDY_BOX, WORK, require, write_json

require(OSM_PBF, how="Run ./01_collect_data.sh first.")

W, S, E, N = STUDY_BOX
NOT_WALKABLE = {
    "abandoned",
    "bus_guideway",
    "busway",  # EDSA's bus lanes
    "emergency_bay",
    "construction",
    "cycleway",
    "motorway",
    "motorway_link",
    "no",
    "planned",
    "platform",
    "proposed",
    "raceway",
    "razed",
    "disused",
    "bus_stop",
    "rest_area",
    "services",
}


def walkable(tags):
    hw = tags.get("highway")
    return (
        hw is not None
        and hw not in NOT_WALKABLE
        and tags.get("area") != "yes"
        and tags.get("foot") != "no"
        and tags.get("access") not in ("private", "no")
        and tags.get("service") != "private"
    )


stamp = osmium.io.Reader(str(OSM_PBF), osmium.osm.NOTHING).header().get("osmosis_replication_timestamp")
print(f"Geofabrik extract snapshot: {stamp}")

u, v, way, cls = array("q"), array("q"), array("q"), array("H")
nodes, footbridges = {}, set()
classes = {}
fp = osmium.FileProcessor(str(OSM_PBF), osmium.osm.NODE | osmium.osm.WAY).with_locations()
for obj in fp.with_filter(osmium.filter.KeyFilter("highway")):
    if not obj.is_way() or not walkable(obj.tags):
        continue
    code = classes.setdefault(obj.tags.get("highway"), len(classes))
    if obj.tags.get("bridge") not in (None, "no") and obj.tags.get("highway") in ("footway", "steps", "path"):
        footbridges.add(obj.id)
    prev = None
    for n in obj.nodes:
        loc = n.location
        here = loc.valid() and W <= loc.lon <= E and S <= loc.lat <= N
        if here:
            nodes[n.ref] = (loc.lon, loc.lat)
            if prev is not None and prev != n.ref:
                u.append(prev)
                v.append(n.ref)
                way.append(obj.id)
                cls.append(code)
        prev = n.ref if here else None

node_ids = np.fromiter(nodes, dtype=np.int64, count=len(nodes))
lonlat = np.array(list(nodes.values()))
idx = pd.Series(np.arange(len(node_ids)), index=node_ids)
ui, vi = idx[np.frombuffer(u, dtype=np.int64)].values, idx[np.frombuffer(v, dtype=np.int64)].values
lon, lat = np.radians(lonlat[:, 0]), np.radians(lonlat[:, 1])
a = np.sin((lat[vi] - lat[ui]) / 2) ** 2 + np.cos(lat[ui]) * np.cos(lat[vi]) * np.sin((lon[vi] - lon[ui]) / 2) ** 2
length = 2 * 6_371_008.8 * np.arcsin(np.sqrt(a))

# Largest connected piece, so nobody is snapped to an island
g = coo_matrix((np.ones(len(ui)), (ui, vi)), shape=(len(node_ids),) * 2)
n_comp, comp = connected_components(g, directed=False)
main = comp == np.bincount(comp).argmax()
keep = main[ui]
names = {c: h for h, c in classes.items()}
edges = pd.DataFrame(
    {
        "u": node_ids[ui[keep]],
        "v": node_ids[vi[keep]],
        "length_m": length[keep].astype("float32"),
        "way_id": np.frombuffer(way, dtype=np.int64)[keep],
        "highway": pd.Categorical([names[c] for c in np.frombuffer(cls, dtype=np.uint16)[keep]]),
    }
)
walk_nodes = pd.DataFrame({"node_id": node_ids[main], "lon": lonlat[main, 0], "lat": lonlat[main, 1]})
edges.to_parquet(WORK / "walk_edges.parquet", index=False)
walk_nodes.to_parquet(WORK / "walk_nodes.parquet", index=False)
for f in ("walk_nodes.parquet", "walk_edges.parquet"):
    print(f"wrote {(WORK / f).relative_to(ROOT)}")

km = edges.groupby("highway", observed=True).length_m.sum().div(1000).sort_values(ascending=False)
stats = {
    "osm_snapshot": stamp,
    "nodes_in_box": len(node_ids),
    "segments_in_box": len(ui),
    "connected_pieces": int(n_comp),
    "nodes_kept": int(main.sum()),
    "share_of_nodes_kept": round(float(main.mean()), 4),
    "segments_kept": len(edges),
    "km_kept": round(float(edges.length_m.sum() / 1000), 1),
    "km_dropped_in_small_pieces": round(float(length[~keep].sum() / 1000), 1),
    "ways_kept": int(edges.way_id.nunique()),
    "footbridge_ways_kept": int(edges.way_id[edges.way_id.isin(footbridges)].nunique()),
    "footbridge_km_kept": round(float(edges.length_m[edges.way_id.isin(footbridges)].sum() / 1000), 1),
    "km_by_highway": {k: round(float(x), 1) for k, x in km.items()},
}
write_json(WORK / "walk_stats.json", stats)
print(
    f"walking network: {stats['nodes_kept']:,} nodes, {stats['segments_kept']:,} segments, {stats['km_kept']:,} km "
    f"(largest connected piece, {stats['share_of_nodes_kept']:.1%} of nodes)"
)
