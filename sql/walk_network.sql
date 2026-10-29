-- The walking network: one row per OSM way segment between consecutive nodes.
-- The way filter copies OSMnx's "walk" network type: any highway a person may walk
-- on, so trunk roads with sidewalks stay in, while expressways (motorway), cycleways,
-- private roads and anything under construction are dropped. Walking is two-way.
COPY (
  WITH walk_ways AS (
    SELECT id, refs
    FROM read_parquet('${WORK}/osm_ways.parquet')
    WHERE tags['highway'] IS NOT NULL
      AND coalesce(tags['area'], '') <> 'yes'
      AND tags['highway'] NOT IN ('abandoned', 'bus_guideway', 'construction', 'cycleway', 'motorway',
                                  'motorway_link', 'no', 'planned', 'platform', 'proposed', 'raceway', 'razed')
      AND coalesce(tags['foot'], '') <> 'no'
      AND coalesce(tags['access'], '') <> 'private'
      AND coalesce(tags['service'], '') <> 'private'
  ), vertices AS (
    SELECT id AS way_id, unnest(refs) AS node_id, generate_subscripts(refs, 1) AS pos
    FROM walk_ways
  )
  SELECT a.node_id AS u,
         b.node_id AS v,
         ST_Distance_Sphere(ST_Point(na.lon, na.lat), ST_Point(nb.lon, nb.lat)) AS length_m
  FROM vertices a
  JOIN vertices b ON b.way_id = a.way_id AND b.pos = a.pos + 1
  JOIN read_parquet('${WORK}/osm_nodes.parquet') na ON na.id = a.node_id
  JOIN read_parquet('${WORK}/osm_nodes.parquet') nb ON nb.id = b.node_id
) TO '${WORK}/walk_edges.parquet' (FORMAT parquet);
