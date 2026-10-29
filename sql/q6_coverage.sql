-- Q6. How complete are the service layers? Overture is the main source for
-- groceries, healthcare and schools; OSM is the cross-check. "matched" is the share
-- of OSM features with an Overture place of the same service within 100 m.
WITH ov AS (
  SELECT service, lon, lat, confidence >= ${MIN_CONFIDENCE} AND coalesce(operating_status, 'open') = 'open' AS used
  FROM read_parquet('${WORK}/overture_places.parquet')
), osm AS (
  SELECT osm_id, service, lon, lat FROM read_parquet('${WORK}/osm_services.parquet') WHERE kind = 'crosscheck'
), matched AS (
  SELECT DISTINCT o.osm_id
  FROM osm o JOIN ov v
    ON v.used AND v.service = o.service
   AND v.lat BETWEEN o.lat - 0.001 AND o.lat + 0.001
   AND v.lon BETWEEN o.lon - 0.001 AND o.lon + 0.001
   AND ST_Distance_Sphere(ST_Point(o.lon, o.lat), ST_Point(v.lon, v.lat)) <= 100
)
SELECT s.service,
       (SELECT count(*) FROM ov WHERE ov.service = s.service) AS overture_all,
       (SELECT count(*) FROM ov WHERE ov.service = s.service AND used) AS overture_used,
       (SELECT count(*) FROM osm WHERE osm.service = s.service) AS osm_features,
       round(100 * (SELECT count(*) FROM osm JOIN matched USING (osm_id) WHERE osm.service = s.service)
             / nullif((SELECT count(*) FROM osm WHERE osm.service = s.service), 0)) AS pct_osm_matched
FROM (VALUES ('grocery'), ('health'), ('schools')) s(service)
ORDER BY s.service;
