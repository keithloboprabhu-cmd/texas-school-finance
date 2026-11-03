-- Campus points (NCES EDGE, latest year); new = first appearing 2016-17 or later
SELECT ncessch, school_name, district_name, lat, lon, is_new, first_year,
       CASE WHEN is_new THEN [168, 67, 42, 220] ELSE [27, 26, 23, 110] END AS color
FROM mart_campuses WHERE is_open;
