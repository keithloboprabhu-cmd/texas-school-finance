-- Campuses whose NCES school ID first appears in 2016-17 or later and that are still open (ISDs and charters)
SELECT ncessch, school_name, district_name, county, is_charter, first_year, lat, lon, askted_status_date
FROM mart_campuses WHERE is_new AND is_open ORDER BY first_year, district_name;
