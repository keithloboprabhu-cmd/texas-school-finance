-- Statewide money cycle for the analysis universe, nominal and real dollars, by school year.
-- Sources (revenue) -> uses (operating by function group, debt service, capital, recapture).
CREATE OR REPLACE TABLE mart_money_cycle_state_year AS
SELECT s.year,
  sum(r.rev_local_mo_tax) AS local_mo_tax, sum(r.rev_local_is_tax) AS local_is_tax,
  sum(r.rev_other_local) AS other_local, sum(r.rev_state) AS state_revenue, sum(r.rev_federal) AS federal_revenue,
  sum(s.op_instruction) AS op_instruction, sum(s.op_instructional_support) AS op_instructional_support,
  sum(s.op_school_leadership) AS op_school_leadership, sum(s.op_student_support) AS op_student_support,
  sum(s.op_transportation) AS op_transportation, sum(s.op_food_service) AS op_food_service,
  sum(s.op_extracurricular) AS op_extracurricular, sum(s.op_general_administration) AS op_general_administration,
  sum(s.op_plant_maintenance_security) AS op_plant_maintenance_security,
  sum(s.op_data_processing) AS op_data_processing, sum(s.op_community_services) AS op_community_services,
  sum(s.operating) AS operating, sum(s.debt_service) AS debt_service, sum(s.capital) AS capital,
  sum(s.recapture_fn91) AS recapture, sum(s.intergovernmental) AS intergovernmental,
  any_value(m.real_factor) AS real_factor
FROM fct_spending_district_year s
JOIN dim_district d USING (cdn)
LEFT JOIN fct_revenue_district_year r USING (cdn, year)
LEFT JOIN (SELECT DISTINCT year, real_factor FROM mart_district_year) m USING (year)
WHERE d.in_analysis OR d.is_closed_isd
GROUP BY s.year;
