-- Property mix of districts that send recapture vs. those that don't, latest year
SELECT m.recapture_paid > 0 AS pays_recapture, count(*) AS districts,
       round(median(p.mineral_share), 3) AS median_mineral_share, round(median(p.residential_share), 3) AS median_residential_share
FROM mart_district_year m JOIN mart_property_mix p ON p.cdn = m.cdn AND p.tax_year = m.year - 1
WHERE m.year = (SELECT max(year) FROM mart_district_year) AND m.is_current GROUP BY 1;
