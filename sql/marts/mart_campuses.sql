-- Campuses (NCES EDGE points). first_year = first school year the NCES school ID appears
-- (2016 = 2015-16 baseline, so "new" means first_year >= 2017, i.e. opened 2016-17 or later).
CREATE OR REPLACE TABLE mart_campuses AS
WITH s AS (
  SELECT ncessch, min(year) AS first_year, max(year) AS last_year,
         arg_max(leaid, year) AS leaid, arg_max(school_name, year) AS school_name,
         arg_max(lat, year) AS lat, arg_max(lon, year) AS lon
  FROM stg_school_points GROUP BY ncessch
), ask AS (
  SELECT "NCES School ID" AS ncessch, max("School Status Date") AS askted_status_date
  FROM stg_askted WHERE "NCES School ID" IS NOT NULL GROUP BY 1
)
SELECT s.*, d.cdn, d.district_name, d.county, d.esc_region, d.is_charter, d.in_analysis,
       s.first_year >= 2017 AS is_new, s.last_year = (SELECT max(year) FROM stg_school_points) AS is_open,
       ask.askted_status_date
FROM s LEFT JOIN dim_district d ON d.leaid = s.leaid
LEFT JOIN ask USING (ncessch);
