-- OpenStreetMap from the Geofabrik extract, read with DuckDB's ST_ReadOSM.
-- Three tables: every node in the study box, every way that is a road, path or a
-- service feature, and every public transport route relation.

COPY (
  SELECT id, lon, lat, tags
  FROM ST_ReadOSM('${OSM_PBF}')
  WHERE kind = 'node'
    AND lon BETWEEN ${XMIN} AND ${XMAX}
    AND lat BETWEEN ${YMIN} AND ${YMAX}
) TO '${WORK}/osm_nodes.parquet' (FORMAT parquet);

COPY (
  SELECT id, tags, refs
  FROM ST_ReadOSM('${OSM_PBF}')
  WHERE kind = 'way'
    AND (tags['highway'] IS NOT NULL
         OR tags['shop'] IN ('supermarket', 'convenience', 'grocery', 'greengrocer')
         OR tags['amenity'] IN ('marketplace', 'hospital', 'clinic', 'doctors', 'pharmacy', 'school')
         OR tags['healthcare'] IS NOT NULL
         OR tags['leisure'] = 'park')
) TO '${WORK}/osm_ways.parquet' (FORMAT parquet);

COPY (
  SELECT id, tags, refs, ref_roles, ref_types
  FROM ST_ReadOSM('${OSM_PBF}')
  WHERE kind = 'relation' AND tags['type'] = 'route'
) TO '${WORK}/osm_routes.parquet' (FORMAT parquet);
