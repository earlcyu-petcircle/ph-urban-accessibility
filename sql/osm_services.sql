-- Service points from OpenStreetMap.
-- Transit comes from OSM because Overture has no jeepney routes and few stops:
--   rail      stop positions of the operating LRT-1, LRT-2 and MRT-3 routes
--             (PNR's Metro Manila service has been suspended since March 2024 for
--             North-South Commuter Railway works, and the Subway is still being built)
--   stop      mapped bus and jeepney stops
--   jeepney   every vertex of a road a jeepney route runs on: jeepneys pick up
--             anywhere along their route, so the route itself is the stop
-- Public markets (amenity=marketplace) top up Overture's thin palengke coverage.
-- Groceries, healthcare, schools and parks are kept only as a cross-check of Overture.
COPY (
  WITH nodes AS (
    SELECT * FROM read_parquet('${WORK}/osm_nodes.parquet')
  ), way_points AS (  -- ways as their mean vertex, good enough for a point feature
    SELECT w.id, any_value(w.tags) AS tags, avg(n.lon) AS lon, avg(n.lat) AS lat
    FROM (SELECT id, tags, unnest(refs) AS node_id FROM read_parquet('${WORK}/osm_ways.parquet')
          WHERE tags['highway'] IS NULL) w
    JOIN nodes n ON n.id = w.node_id
    GROUP BY w.id
  ), features AS (
    SELECT 'n' || id AS osm_id, tags, lon, lat FROM nodes
    UNION ALL
    SELECT 'w' || id, tags, lon, lat FROM way_points
  ), routes AS (
    SELECT id, tags,
           unnest(refs) AS ref, unnest(ref_roles) AS role, unnest(ref_types) AS ref_type
    FROM read_parquet('${WORK}/osm_routes.parquet')
  ), rail AS (
    SELECT DISTINCT 'n' || n.id AS osm_id, 'transit' AS service, 'rail' AS kind,
           coalesce(n.tags['name'], r.tags['name']) AS name, n.lon, n.lat, n.id AS node_id
    FROM routes r JOIN nodes n ON n.id = r.ref
    WHERE r.tags['network'] IN ('Manila LRT', 'Manila MRT')
      AND r.ref_type = 'node' AND r.role LIKE 'stop%'
  ), stops AS (
    SELECT osm_id, 'transit', 'stop', tags['name'], lon, lat, NULL::BIGINT
    FROM features
    WHERE osm_id LIKE 'n%'
      AND (tags['highway'] = 'bus_stop'
           OR (tags['public_transport'] = 'platform' AND tags['railway'] IS NULL))
  ), jeepney_ways AS (
    SELECT DISTINCT ref AS way_id
    FROM routes
    WHERE ref_type = 'way'
      AND (tags['route'] = 'share_taxi' OR tags['bus'] = 'share_taxi'
           OR regexp_matches(coalesce(tags['network'], '') || ' ' || coalesce(tags['name'], ''), 'PUJ|[Jj]eep'))
  ), jeepney AS (
    SELECT DISTINCT 'n' || n.id, 'transit', 'jeepney', NULL::VARCHAR, n.lon, n.lat, n.id
    FROM (SELECT unnest(refs) AS node_id FROM read_parquet('${WORK}/osm_ways.parquet')
          WHERE id IN (SELECT way_id FROM jeepney_ways)) j
    JOIN nodes n ON n.id = j.node_id
  ), markets AS (
    SELECT osm_id, 'grocery', 'palengke', tags['name'], lon, lat, NULL::BIGINT
    FROM features WHERE tags['amenity'] = 'marketplace'
  ), crosscheck AS (
    SELECT osm_id,
           CASE
             WHEN tags['shop'] IN ('supermarket', 'convenience', 'grocery', 'greengrocer') THEN 'grocery'
             WHEN tags['amenity'] IN ('hospital', 'clinic', 'doctors', 'pharmacy')
                  OR tags['healthcare'] IS NOT NULL THEN 'health'
             WHEN tags['amenity'] = 'school' THEN 'schools'
             WHEN tags['leisure'] = 'park' THEN 'parks'
           END AS service,
           'crosscheck', tags['name'], lon, lat, NULL::BIGINT
    FROM features
    WHERE tags['shop'] IN ('supermarket', 'convenience', 'grocery', 'greengrocer')
       OR tags['amenity'] IN ('hospital', 'clinic', 'doctors', 'pharmacy', 'school')
       OR tags['healthcare'] IS NOT NULL
       OR tags['leisure'] = 'park'
  )
  SELECT * FROM rail
  UNION ALL SELECT * FROM stops
  UNION ALL SELECT * FROM jeepney
  UNION ALL SELECT * FROM markets
  UNION ALL SELECT * FROM crosscheck
) TO '${WORK}/osm_services.parquet' (FORMAT parquet);
