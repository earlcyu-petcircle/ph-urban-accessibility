-- Q3. Is access organised around the rail lines? Residents grouped by their walk
-- to the nearest LRT-1, LRT-2 or MRT-3 stop.
SELECT CASE WHEN d_rail <= 750  THEN '1. within 10 min (750 m)'
            WHEN d_rail <= 1500 THEN '2. 10-20 min (750 m-1.5 km)'
            WHEN d_rail <= 3000 THEN '3. 20-40 min (1.5-3 km)'
            WHEN d_rail <= 5000 THEN '4. 40-67 min (3-5 km)'
            ELSE '5. over 67 min (5 km+)' END AS walk_to_rail,
       sum(pop)::BIGINT AS people,
       round(100 * sum(pop) / sum(sum(pop)) OVER (), 1) AS pct_people,
       round(sum(pop * s_composite) / sum(pop), 1) AS composite,
       round(sum(pop * s_grocery) / sum(pop)) AS grocery,
       round(sum(pop * s_health)  / sum(pop)) AS health,
       round(sum(pop * s_parks)   / sum(pop)) AS parks,
       round(sum(pop * s_transit) / sum(pop)) AS transit,
       round(sum(pop * s_schools) / sum(pop)) AS schools
FROM residents
GROUP BY ALL
ORDER BY walk_to_rail;
