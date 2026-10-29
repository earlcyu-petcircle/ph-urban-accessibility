-- Barangay scores: population-weighted means of the resident scores, the share of
-- residents within a 5 and 10 minute walk, and the median resident's distance,
-- for every service plus the palengke and rail extras.
CREATE OR REPLACE TABLE barangay_scores AS
WITH long AS (
  UNPIVOT (SELECT pcode, pop, d_grocery AS grocery, d_health AS health, d_parks AS parks,
                  d_transit AS transit, d_schools AS schools, d_palengke AS palengke, d_rail AS rail
           FROM residents)
  ON grocery, health, parks, transit, schools, palengke, rail
  INTO NAME service VALUE dist_m
), ranked AS (
  SELECT *,
         sum(pop) OVER (PARTITION BY pcode, service ORDER BY dist_m
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_pop,
         sum(pop) OVER (PARTITION BY pcode, service) AS tot_pop
  FROM long
), by_service AS (
  SELECT pcode, service,
         sum(pop) FILTER (WHERE dist_m <= ${T5})  / any_value(tot_pop) AS share_5,
         sum(pop) FILTER (WHERE dist_m <= ${T10}) / any_value(tot_pop) AS share_10,
         sum(pop) FILTER (WHERE dist_m <= ${T15}) / any_value(tot_pop) AS share_15,
         min(dist_m) FILTER (WHERE cum_pop >= tot_pop / 2) AS median_m
  FROM ranked
  GROUP BY ALL
), wide AS (
  PIVOT by_service ON service IN ('grocery', 'health', 'parks', 'transit', 'schools', 'palengke', 'rail')
  USING coalesce(any_value(share_5), 0) AS share5, coalesce(any_value(share_10), 0) AS share10,
        coalesce(any_value(share_15), 0) AS share15, any_value(median_m) AS median_m
  GROUP BY pcode
), composite AS (
  SELECT pcode,
         sum(pop) AS pop_placed,
         sum(pop * s_composite) / sum(pop) AS composite,
         sum(pop * s_grocery) / sum(pop) AS score_grocery,
         sum(pop * s_health)  / sum(pop) AS score_health,
         sum(pop * s_parks)   / sum(pop) AS score_parks,
         sum(pop * s_transit) / sum(pop) AS score_transit,
         sum(pop * s_schools) / sum(pop) AS score_schools
  FROM residents
  GROUP BY pcode
)
SELECT b.pcode, b.barangay, b.city, b.district, b.pop2020, b.area_km2, b.density_km2, b.place_lived,
       c.* EXCLUDE (pcode), w.* EXCLUDE (pcode)
FROM barangays b
LEFT JOIN composite c USING (pcode)
LEFT JOIN wide w USING (pcode);
