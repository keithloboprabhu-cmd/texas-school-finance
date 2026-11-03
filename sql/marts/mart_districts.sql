-- One row per analysis district: identifiers, geography and latest community wealth/need.
CREATE OR REPLACE TABLE mart_districts AS
SELECT d.cdn, d.leaid, d.geoid, d.district_name, d.county, d.county_fips, d.esc_region,
       d.locale, d.locale_detail, d.is_metro, d.cbsa_name,
       d.int_lat AS lat, d.int_lon AS lon, d.aland / 2.59e6 AS land_sq_miles,
       s.child_poverty_rate, s.pop_5_17, s.saipe_year,
       a.median_household_income, a.median_household_income >= 250001 AS income_topcoded,
       a.median_home_value, a.total_population, a.acs_vintage,
       t.econ_disadv_pct, t.english_learners_pct, t.special_ed_pct, t.tapr_students, t.tapr_year
FROM dim_district d
LEFT JOIN stg_saipe s ON s.geoid = d.geoid
LEFT JOIN stg_acs a ON a.geoid = d.geoid
LEFT JOIN stg_tapr t ON t.cdn = d.cdn
WHERE d.in_analysis;
