-- M&O and I&S rates over time for the 10 largest districts (latest enrollment)
WITH big AS (
  SELECT cdn FROM mart_district_year WHERE year = (SELECT max(year) FROM mart_district_year) AND is_current
  ORDER BY enrollment DESC LIMIT 10
)
SELECT t.cdn, t.district_name, t.year, t.mo_rate, t.is_rate FROM mart_tax_rates t JOIN big USING (cdn) ORDER BY t.district_name, t.year;
