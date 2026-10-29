-- Put every barangay's 2020 census population into its buildings.
-- Three layers, coarse to fine:
--   1. the census fixes how many people live in each barangay;
--   2. WorldPop's 100 m grid says which parts of the barangay are lived in;
--   3. within a 100 m cell, people go to buildings in proportion to footprint area.
-- Buildings tagged as clearly non-residential (shops, schools, churches, factories...)
-- get no one; untagged buildings, about 81% of them, stay in.
-- If a barangay's buildings all sit in cells WorldPop leaves empty, footprint area
-- alone is the weight. A barangay with no building at all gets one origin point.
COPY (
  WITH b AS (
    SELECT bg.id, bg.lon, bg.lat, bg.area_m2, bg.cell, bg.wp_cell, br.pcode
    FROM buildings bg
    JOIN barangays br ON ST_Contains(br.geom, ST_Point(bg.lon, bg.lat))
    WHERE bg.area_m2 >= 10
      AND coalesce(bg.subtype, 'residential') = 'residential'
  ), w AS (
    SELECT *,
           wp_cell * area_m2 / sum(area_m2) OVER (PARTITION BY cell) AS w_grid,
           area_m2 AS w_area
    FROM b
  ), wb AS (
    SELECT *,
           sum(w_grid) OVER (PARTITION BY pcode) AS sum_grid,
           sum(w_area) OVER (PARTITION BY pcode) AS sum_area
    FROM w
  ), origins AS (
    SELECT wb.id AS origin_id, wb.pcode, wb.lon, wb.lat,
           br.pop2020 * CASE WHEN sum_grid > 0 THEN w_grid / sum_grid ELSE w_area / sum_area END AS pop,
           CASE WHEN sum_grid > 0 THEN 'buildings x WorldPop' ELSE 'buildings by area' END AS method
    FROM wb JOIN barangays br USING (pcode)
  )
  SELECT * FROM origins WHERE pop > 0
  UNION ALL
  SELECT 'centroid:' || pcode, pcode, ST_X(ST_PointOnSurface(geom)), ST_Y(ST_PointOnSurface(geom)),
         pop2020, 'barangay point'
  FROM barangays
  WHERE pop2020 > 0 AND pcode NOT IN (SELECT pcode FROM origins)
) TO '${WORK}/origins.parquet' (FORMAT parquet);
