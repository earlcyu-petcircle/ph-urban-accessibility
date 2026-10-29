-- Parks as polygons: Overture base land_use (assembled from OpenStreetMap leisure tags).
-- Public green space only: parks, village greens and recreation grounds of at least 0.1 ha.
-- Pitches, playgrounds, golf courses, cemeteries and protected areas are left out.
COPY (
  SELECT id,
         class,
         names.primary               AS name,
         ST_Area_Spheroid(geometry)  AS area_m2,
         ST_AsWKB(geometry)          AS wkb
  FROM read_parquet('${OVERTURE}/theme=base/type=land_use/*', hive_partitioning = 1)
  WHERE bbox.xmin BETWEEN ${XMIN} AND ${XMAX}
    AND bbox.ymin BETWEEN ${YMIN} AND ${YMAX}
    AND class IN ('park', 'village_green', 'recreation_ground')
    AND ST_Area_Spheroid(geometry) >= 1000
) TO '${WORK}/overture_parks.parquet' (FORMAT parquet);
