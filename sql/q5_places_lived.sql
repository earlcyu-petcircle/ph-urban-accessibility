-- Q5. How do the three places I have lived compare? Tondo is the whole district
-- (259 barangays), so its figures are resident-weighted across all of them.
-- percentile = share of Metro Manila residents whose barangay scores lower.
WITH ranked AS (
  SELECT *, sum(pop2020) OVER (ORDER BY composite ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
              / sum(pop2020) OVER () AS below_share
  FROM barangay_scores WHERE pop2020 > 0
)
SELECT place_lived,
       count(*) AS barangays,
       sum(pop2020) AS people,
       round(sum(pop2020 * composite) / sum(pop2020), 1) AS composite,
       round(100 * sum(pop2020 * below_share) / sum(pop2020)) AS percentile,
       round(sum(pop2020 * score_grocery) / sum(pop2020)) AS grocery,
       round(sum(pop2020 * score_health)  / sum(pop2020)) AS health,
       round(sum(pop2020 * score_parks)   / sum(pop2020)) AS parks,
       round(sum(pop2020 * score_transit) / sum(pop2020)) AS transit,
       round(sum(pop2020 * score_schools) / sum(pop2020)) AS schools,
       round(100 * sum(pop2020 * grocery_share5) / sum(pop2020)) AS pct_grocery_5min,
       round(100 * sum(pop2020 * palengke_share10) / sum(pop2020)) AS pct_palengke_10min,
       round(100 * sum(pop2020 * parks_share5) / sum(pop2020)) AS pct_park_5min,
       round(100 * sum(pop2020 * rail_share15) / sum(pop2020)) AS pct_rail_15min,
       min(round(composite, 1)) AS worst_barangay_score,
       max(round(composite, 1)) AS best_barangay_score
FROM ranked
WHERE place_lived IS NOT NULL
GROUP BY place_lived
ORDER BY composite DESC;
