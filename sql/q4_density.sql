-- Q4. Equity: do crowded barangays get less? Barangays are sorted by population
-- density and cut into ten groups of roughly equal population (about 1.35 million
-- people each), so every decile is a tenth of Metro Manila's residents.
WITH b AS (
  SELECT *, sum(pop2020) OVER (ORDER BY density_km2, pcode) / sum(pop2020) OVER () AS cum_share
  FROM barangays WHERE pop2020 > 0
), d AS (
  SELECT pcode, density_km2, least(10, ceil(cum_share * 10))::INT AS density_decile FROM b
)
SELECT d.density_decile,
       count(DISTINCT d.pcode) AS barangays,
       sum(r.pop)::BIGINT AS people,
       round(min(d.density_km2), -2)::BIGINT AS min_density_km2,
       round(max(d.density_km2), -2)::BIGINT AS max_density_km2,
       round(sum(r.pop * r.s_composite) / sum(r.pop), 1) AS composite,
       round(100 * sum(r.pop) FILTER (WHERE r.d_grocery  <= ${T5}) / sum(r.pop)) AS pct_grocery_5min,
       round(100 * sum(r.pop) FILTER (WHERE r.d_palengke <= ${T10}) / sum(r.pop)) AS pct_palengke_10min,
       round(100 * sum(r.pop) FILTER (WHERE r.d_health   <= ${T5}) / sum(r.pop)) AS pct_health_5min,
       round(100 * sum(r.pop) FILTER (WHERE r.d_parks    <= ${T5}) / sum(r.pop)) AS pct_park_5min,
       round(100 * sum(r.pop) FILTER (WHERE r.d_transit  <= ${T5}) / sum(r.pop)) AS pct_transit_5min,
       round(100 * sum(r.pop) FILTER (WHERE r.d_schools  <= ${T5}) / sum(r.pop)) AS pct_school_5min,
       round(sum(r.pop * r.d_parks) / sum(r.pop))::INT AS mean_walk_to_park_m
FROM residents r JOIN d USING (pcode)
GROUP BY d.density_decile
ORDER BY d.density_decile;
