-- Revenue mix (all funds) for $cdn by school year
SELECT year, rev_local, rev_state, rev_federal, share_local, share_state, share_federal
FROM mart_district_year WHERE cdn = $cdn ORDER BY year;
