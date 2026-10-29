-- Q1. Which barangays have the best and worst walking access?
-- Ranked on the composite score among barangays of at least 10,000 people, so a
-- one-block barangay of 300 people cannot top the list on a technicality.
SELECT rank() OVER (ORDER BY composite DESC) AS best_rank,
       rank() OVER (ORDER BY composite ASC)  AS worst_rank,
       barangay, city, district, pop2020,
       round(composite, 1) AS composite,
       round(score_grocery) AS grocery, round(score_health) AS health, round(score_parks) AS parks,
       round(score_transit) AS transit, round(score_schools) AS schools
FROM barangay_scores
WHERE pop2020 >= 10000
QUALIFY best_rank <= 10 OR worst_rank <= 10
ORDER BY composite DESC;
