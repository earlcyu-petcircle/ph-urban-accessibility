-- Overture building footprints in the study box: centroid, footprint area and type.
-- These are where people are placed (src/population.py), not services.
COPY (
  SELECT id,
         subtype,
         ST_Area_Spheroid(geometry)      AS area_m2,
         ST_X(ST_Centroid(geometry))     AS lon,
         ST_Y(ST_Centroid(geometry))     AS lat
  FROM read_parquet('${OVERTURE}/theme=buildings/type=building/*', hive_partitioning = 1)
  WHERE bbox.xmin BETWEEN ${XMIN} AND ${XMAX}
    AND bbox.ymin BETWEEN ${YMIN} AND ${YMAX}
) TO '${WORK}/overture_buildings.parquet' (FORMAT parquet);
