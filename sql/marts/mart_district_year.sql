-- One row per district and school year: current analysis districts (ISD/common district with a
-- boundary) plus consolidated/closed districts for the years they reported (is_current = FALSE).
-- Dollars: nominal and real (CPI-U, July-June school-year average, in dollars of the latest
-- PEIMS year). Per-student figures divide by fall enrollment (`enrollment`).
CREATE OR REPLACE TABLE mart_district_year AS
WITH latest AS (SELECT max(year) AS y FROM fct_spending_district_year),
cpi AS (
  SELECT c.year, (SELECT cpi FROM stg_cpi WHERE year = (SELECT y FROM latest)) / c.cpi AS real_factor
  FROM stg_cpi c
)
SELECT
  d.cdn, s.year, d.in_analysis AS is_current, d.district_name, d.county, d.esc_region, d.locale, d.locale_detail, d.is_metro,
  e.enrollment,
  e.enrollment < 500 AS small_district,
  cpi.real_factor,
  -- spending (nominal)
  s.operating, s.operating_tea_def, s.ssa_agent_operating,
  s.debt_service, s.capital, s.recapture_fn91, s.intergovernmental,
  -- per student, real dollars
  s.operating * cpi.real_factor / nullif(e.enrollment, 0)                 AS op_per_student_real,
  s.operating / nullif(e.enrollment, 0)                                   AS op_per_student_nominal,
  s.op_instruction * cpi.real_factor / nullif(e.enrollment, 0)            AS instruction_per_student_real,
  s.op_instructional_support * cpi.real_factor / nullif(e.enrollment, 0)  AS instructional_support_per_student_real,
  s.op_school_leadership * cpi.real_factor / nullif(e.enrollment, 0)      AS school_leadership_per_student_real,
  s.op_student_support * cpi.real_factor / nullif(e.enrollment, 0)        AS student_support_per_student_real,
  s.op_transportation * cpi.real_factor / nullif(e.enrollment, 0)         AS transportation_per_student_real,
  s.op_food_service * cpi.real_factor / nullif(e.enrollment, 0)           AS food_service_per_student_real,
  s.op_extracurricular * cpi.real_factor / nullif(e.enrollment, 0)        AS extracurricular_per_student_real,
  s.op_general_administration * cpi.real_factor / nullif(e.enrollment, 0) AS general_administration_per_student_real,
  s.op_plant_maintenance_security * cpi.real_factor / nullif(e.enrollment, 0) AS plant_maintenance_security_per_student_real,
  s.op_data_processing * cpi.real_factor / nullif(e.enrollment, 0)        AS data_processing_per_student_real,
  s.op_community_services * cpi.real_factor / nullif(e.enrollment, 0)     AS community_services_per_student_real,
  s.capital * cpi.real_factor / nullif(e.enrollment, 0)                   AS capital_per_student_real,
  s.debt_service * cpi.real_factor / nullif(e.enrollment, 0)              AS debt_service_per_student_real,
  -- revenue mix
  r.rev_local, r.rev_state, r.rev_federal, r.rev_total,
  r.rev_local / nullif(r.rev_total, 0)   AS share_local,
  r.rev_state / nullif(r.rev_total, 0)   AS share_state,
  r.rev_federal / nullif(r.rev_total, 0) AS share_federal,
  -- property wealth
  w.tax_year, w.property_value, w.value_source,
  w.property_value * cpi.real_factor / nullif(e.enrollment, 0)            AS wealth_per_student_real,
  w.property_value / nullif(e.enrollment, 0)                              AS wealth_per_student_nominal,
  -- recapture (TEA "Recapture Paid by District"; zero when not listed)
  coalesce(rp.recapture_paid, 0)                                          AS recapture_paid,
  coalesce(rp.recapture_paid, 0) * cpi.real_factor / nullif(e.enrollment, 0) AS recapture_per_student_real,
  coalesce(rp.designated, FALSE)                                          AS recapture_designated,
  -- tax rates
  t.mo_rate, t.is_rate
FROM dim_district d
JOIN fct_spending_district_year s USING (cdn)
LEFT JOIN fct_enrollment_district_year e USING (cdn, year)
LEFT JOIN fct_revenue_district_year r USING (cdn, year)
LEFT JOIN fct_wealth_district_year w USING (cdn, year)
LEFT JOIN stg_recapture_paid rp USING (cdn, year)
LEFT JOIN stg_tax_rates t USING (cdn, year)
LEFT JOIN cpi USING (year)
WHERE d.in_analysis OR d.is_closed_isd;

-- ---------------------------------------------------------------------------------------------
-- Source-data anomalies. Per-student figures for these district-years are removed (set to NULL)
-- so they don't distort maps, rankings, the model or the equity measures. Dollar totals are kept.
--   out_of_bounds    : real operating spending per student below $5,000 or above $60,000
--   spending_spike   : per-student spending more than 2x BOTH the previous and the
--                      next year for the same district (a one-year reporting error)
--   enrollment_spike : enrollment more than 1.5x BOTH neighbouring years
-- Every removed row is listed in data/qa/anomalies.csv.
ALTER TABLE mart_district_year ADD COLUMN data_anomaly VARCHAR;
ALTER TABLE mart_district_year ADD COLUMN reported_op_per_student_real DOUBLE;
UPDATE mart_district_year AS m SET data_anomaly = x.reason, reported_op_per_student_real = x.op_per_student_real
FROM (
  SELECT cdn, year, op_per_student_real,
    CASE
      WHEN op_per_student_real < 5000 OR op_per_student_real > 60000 THEN 'out_of_bounds'
      WHEN prev_p IS NOT NULL AND next_p IS NOT NULL
           AND op_per_student_real > 2 * prev_p AND op_per_student_real > 2 * next_p THEN 'spending_spike'
      WHEN prev_e >= 100 AND next_e >= 100
           AND enrollment > 1.5 * prev_e AND enrollment > 1.5 * next_e THEN 'enrollment_spike'
    END AS reason
  FROM (
    SELECT cdn, year, enrollment, op_per_student_real,
      lag(op_per_student_real) OVER w AS prev_p, lead(op_per_student_real) OVER w AS next_p,
      lag(enrollment) OVER w AS prev_e, lead(enrollment) OVER w AS next_e
    FROM mart_district_year WINDOW w AS (PARTITION BY cdn ORDER BY year)
  )
) x
WHERE m.cdn = x.cdn AND m.year = x.year AND x.reason IS NOT NULL;

UPDATE mart_district_year SET
  op_per_student_real = NULL, op_per_student_nominal = NULL,
  instruction_per_student_real = NULL, instructional_support_per_student_real = NULL,
  school_leadership_per_student_real = NULL, student_support_per_student_real = NULL,
  transportation_per_student_real = NULL, food_service_per_student_real = NULL,
  extracurricular_per_student_real = NULL, general_administration_per_student_real = NULL,
  plant_maintenance_security_per_student_real = NULL, data_processing_per_student_real = NULL,
  community_services_per_student_real = NULL, capital_per_student_real = NULL,
  debt_service_per_student_real = NULL,
  wealth_per_student_real = CASE WHEN data_anomaly = 'enrollment_spike' THEN NULL ELSE wealth_per_student_real END,
  wealth_per_student_nominal = CASE WHEN data_anomaly = 'enrollment_spike' THEN NULL ELSE wealth_per_student_nominal END,
  recapture_per_student_real = CASE WHEN data_anomaly = 'enrollment_spike' THEN NULL ELSE recapture_per_student_real END
WHERE data_anomaly IS NOT NULL;
