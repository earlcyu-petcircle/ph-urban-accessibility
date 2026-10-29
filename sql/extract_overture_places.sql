-- Overture places in the study box, sorted into services.
-- One row per place; `service` is NULL for places that are not a service used here.
-- The palengke (public wet market) flag sits inside grocery.
COPY (
  WITH p AS (
    SELECT id,
           names.primary       AS name,
           taxonomy.primary    AS category,
           taxonomy.hierarchy  AS hierarchy,
           confidence,
           operating_status,
           sources[1].dataset  AS source_dataset,
           ST_X(geometry)      AS lon,
           ST_Y(geometry)      AS lat
    FROM read_parquet('${OVERTURE}/theme=places/type=place/*', hive_partitioning = 1)
    WHERE bbox.xmin BETWEEN ${XMIN} AND ${XMAX}
      AND bbox.ymin BETWEEN ${YMIN} AND ${YMAX}
  ), classified AS (
    SELECT *,
      list_has_any(hierarchy, ['farmers_market', 'public_market'])
        OR (list_contains(hierarchy, 'shopping')
            AND regexp_matches(coalesce(name, ''), '(?i)palengke|public market|wet market|mercado|talipapa'))
        AS is_palengke,
      CASE
        WHEN list_has_any(hierarchy, ['grocery_store', 'supermarket', 'convenience_store',
                                      'farmers_market', 'public_market'])
          OR category IN ('produce_store', 'butcher_shop', 'fishmonger')
          THEN 'grocery'
        WHEN list_has_any(hierarchy, ['hospital', 'primary_care_or_general_clinic',
                                      'emergency_or_urgent_care_facility', 'pharmacy_and_drug_store'])
          OR category IN ('health_care', 'outpatient_care_facility', 'pediatric_clinic', 'maternity_center')
          THEN 'health'
        WHEN category IN ('school', 'elementary_school', 'middle_school', 'high_school',
                          'public_school', 'private_school')
          THEN 'schools'
        WHEN category = 'bus_station'
          THEN 'transit'
      END AS service
    FROM p
  )
  SELECT id, name, category, confidence, operating_status, source_dataset, lon, lat,
         CASE WHEN is_palengke THEN 'grocery' ELSE service END AS service,
         is_palengke
  FROM classified
  WHERE service IS NOT NULL OR is_palengke
) TO '${WORK}/overture_places.parquet' (FORMAT parquet);
