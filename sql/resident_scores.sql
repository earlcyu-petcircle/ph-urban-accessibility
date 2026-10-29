-- One row per lived-in building: its people, its walking distances, and its scores.
-- A service scores 100 within a 5 minute walk (375 m), 67 within 10 (750 m),
-- 33 within 15 (1,125 m) and 0 beyond. This is the mean of the three "within"
-- flags, so a barangay's score is also the mean of its 5, 10 and 15 minute shares.
-- The composite gives the five services equal weight.
CREATE OR REPLACE VIEW residents AS
WITH d AS (
  SELECT * FROM read_parquet('${WORK}/origin_dist.parquet')
), s AS (
  SELECT *,
    100 * ((d_grocery <= ${T5})::INT + (d_grocery <= ${T10})::INT + (d_grocery <= ${T15})::INT) / 3 AS s_grocery,
    100 * ((d_health  <= ${T5})::INT + (d_health  <= ${T10})::INT + (d_health  <= ${T15})::INT) / 3 AS s_health,
    100 * ((d_parks   <= ${T5})::INT + (d_parks   <= ${T10})::INT + (d_parks   <= ${T15})::INT) / 3 AS s_parks,
    100 * ((d_transit <= ${T5})::INT + (d_transit <= ${T10})::INT + (d_transit <= ${T15})::INT) / 3 AS s_transit,
    100 * ((d_schools <= ${T5})::INT + (d_schools <= ${T10})::INT + (d_schools <= ${T15})::INT) / 3 AS s_schools
  FROM d
)
SELECT *, (s_grocery + s_health + s_parks + s_transit + s_schools) / 5 AS s_composite
FROM s;
