-- One row per analysis district: identifiers, geography and latest community wealth/need.
-- enrollment_caution (data-only flag): >= 25% of the district's Oct-2025 AskTED campus enrollment is
-- on campuses TEA marks "Virtual", or latest PEIMS fall enrollment differs from the AskTED campus
-- total by more than 50% and more than 500 students. Such districts enroll many students who do not
-- live in the district, so per-student and growth figures are not comparable; they are excluded
-- from the wealth-spending model, peers and equity metrics, and labelled wherever shown.
CREATE OR REPLACE TABLE mart_districts AS
WITH ask AS (
  SELECT "District Number" AS cdn,
         sum(TRY_CAST("School Enrollment as of Oct 2025" AS DOUBLE)) AS askted_enrollment,
         sum(TRY_CAST("School Enrollment as of Oct 2025" AS DOUBLE)) FILTER (WHERE "Virtual/Hybrid Campus" = 'Virtual') AS virtual_enrollment
  FROM stg_askted GROUP BY 1
), pe AS (
  SELECT cdn, enrollment AS peims_enrollment_latest FROM fct_enrollment_district_year
  WHERE year = (SELECT max(year) FROM fct_enrollment_district_year)
)
SELECT d.cdn, d.leaid, d.geoid, d.district_name, d.county, d.county_fips, d.esc_region,
       d.locale, d.locale_detail, d.is_metro, d.cbsa_name,
       d.int_lat AS lat, d.int_lon AS lon, d.aland / 2.59e6 AS land_sq_miles,
       s.child_poverty_rate, s.pop_5_17, s.saipe_year,
       a.median_household_income, a.median_household_income >= 250001 AS income_topcoded,
       a.median_home_value, a.total_population, a.acs_vintage,
       t.econ_disadv_pct, t.english_learners_pct, t.special_ed_pct, t.tapr_students, t.tapr_year,
       ask.askted_enrollment, coalesce(ask.virtual_enrollment, 0) / nullif(ask.askted_enrollment, 0) AS virtual_share,
       pe.peims_enrollment_latest,
       coalesce(coalesce(ask.virtual_enrollment, 0) / nullif(ask.askted_enrollment, 0) >= 0.25, FALSE)
         OR (abs(pe.peims_enrollment_latest - ask.askted_enrollment) > 0.5 * ask.askted_enrollment
             AND abs(pe.peims_enrollment_latest - ask.askted_enrollment) > 500) AS enrollment_caution
FROM dim_district d
LEFT JOIN ask USING (cdn)
LEFT JOIN pe USING (cdn)
LEFT JOIN stg_saipe s ON s.geoid = d.geoid
LEFT JOIN stg_acs a ON a.geoid = d.geoid
LEFT JOIN stg_tapr t ON t.cdn = d.cdn
WHERE d.in_analysis;
