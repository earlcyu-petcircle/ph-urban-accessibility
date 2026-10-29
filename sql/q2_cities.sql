-- Q2. How do the 17 cities compare? Resident-weighted, so a city's score is its
-- average resident's score, and the 5 minute shares count people, not barangays.
SELECT b.city,
       sum(r.pop)::BIGINT AS people,
       round(sum(r.pop * r.s_composite) / sum(r.pop), 1) AS composite,
       round(sum(r.pop * r.s_grocery) / sum(r.pop)) AS grocery,
       round(sum(r.pop * r.s_health)  / sum(r.pop)) AS health,
       round(sum(r.pop * r.s_parks)   / sum(r.pop)) AS parks,
       round(sum(r.pop * r.s_transit) / sum(r.pop)) AS transit,
       round(sum(r.pop * r.s_schools) / sum(r.pop)) AS schools,
       round(100 * sum(r.pop) FILTER (WHERE r.d_grocery <= ${T5}) / sum(r.pop)) AS pct_grocery_5min,
       round(100 * sum(r.pop) FILTER (WHERE r.d_parks <= ${T5}) / sum(r.pop)) AS pct_park_5min
FROM residents r JOIN barangays b USING (pcode)
GROUP BY b.city
ORDER BY composite DESC;
