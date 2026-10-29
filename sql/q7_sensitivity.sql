-- Q7. Do the headline choices drive the result? Two alternative composites:
--   allconf    groceries, healthcare and schools from every Overture record, whatever its confidence
--   nojeepney  transit counts only rail stops, mapped stops and terminals, not the jeepney routes
-- For each: the metro-wide composite, and how closely the barangay ranking agrees with
-- the main one (Spearman rank correlation across barangays).
WITH flags AS (
  SELECT pcode, pop,
         100 * ((d_grocery_allconf <= ${T5})::INT + (d_grocery_allconf <= ${T10})::INT + (d_grocery_allconf <= ${T15})::INT) / 3 AS s_grocery_allconf,
         100 * ((d_health_allconf  <= ${T5})::INT + (d_health_allconf  <= ${T10})::INT + (d_health_allconf  <= ${T15})::INT) / 3 AS s_health_allconf,
         100 * ((d_schools_allconf <= ${T5})::INT + (d_schools_allconf <= ${T10})::INT + (d_schools_allconf <= ${T15})::INT) / 3 AS s_schools_allconf,
         100 * ((d_transit_nojeepney <= ${T5})::INT + (d_transit_nojeepney <= ${T10})::INT + (d_transit_nojeepney <= ${T15})::INT) / 3 AS s_transit_nojeepney,
         s_grocery, s_health, s_parks, s_transit, s_schools, s_composite
  FROM residents
), alt AS (
  SELECT pcode, pop,
         s_composite AS main,
         (s_grocery_allconf + s_health_allconf + s_parks + s_transit + s_schools_allconf) / 5 AS allconf,
         (s_grocery + s_health + s_parks + s_transit_nojeepney + s_schools) / 5 AS nojeepney
  FROM flags
), b AS (
  SELECT pcode, sum(pop * main) / sum(pop) AS main, sum(pop * allconf) / sum(pop) AS allconf,
         sum(pop * nojeepney) / sum(pop) AS nojeepney
  FROM alt GROUP BY pcode
), metro AS (
  SELECT sum(pop * main) / sum(pop) AS main, sum(pop * allconf) / sum(pop) AS allconf,
         sum(pop * nojeepney) / sum(pop) AS nojeepney
  FROM alt
), ranks AS (
  SELECT rank() OVER (ORDER BY main) AS r_main, rank() OVER (ORDER BY allconf) AS r_allconf,
         rank() OVER (ORDER BY nojeepney) AS r_nojeepney
  FROM b
)
SELECT 'all Overture records' AS variant, round((SELECT allconf FROM metro), 1) AS metro_composite,
       round((SELECT main FROM metro), 1) AS main_composite,
       round((SELECT corr(r_main, r_allconf) FROM ranks), 3) AS spearman_vs_main
UNION ALL
SELECT 'transit without jeepney routes', round((SELECT nojeepney FROM metro), 1),
       round((SELECT main FROM metro), 1), round((SELECT corr(r_main, r_nojeepney) FROM ranks), 3);
