-- Spending by district and school year, from PEIMS single-file actuals (all funds).
-- Codes and groups: sql/ref/function_groups.sql, object_groups.sql, fund_groups.sql (FASRG v20).
--
-- operating_tea_def : TEA's operating definition (objects 6100-6400; functions flagged in_operating;
--                     excluding capital projects funds 6xx). Reproduces TEA's published operating
--                     total (tests/test_definitions.py).
-- operating         : HEADLINE. operating_tea_def minus spending in shared services arrangement
--                     fiscal-agent funds (291-379, 431-459), which a fiscal agent spends on behalf
--                     of member districts. Members' own payments to the fiscal agent (function 93)
--                     are already excluded, so SSA-provided services are not counted for anyone.
-- Excluded from operating, reported separately: debt service (object 6500), capital outlay
-- (object 6600), facilities acquisition and construction (function 81), recapture (function 91)
-- and intergovernmental charges (functions 93, 97, 99).
CREATE OR REPLACE TABLE fct_spending_district_year AS
WITH a AS (
  SELECT s.*, g.function_group, g.in_operating, o.is_operating_object,
         g.in_operating AND o.is_operating_object AND s.fund_group <> 'capital_projects' AS op_tea,
         s.fund_group LIKE 'ssa_fiscal_agent%' AS is_ssa_agent
  FROM stg_peims_actuals s
  JOIN ref_function_groups g USING (function)
  JOIN ref_object_groups o USING (object_series)
)
SELECT cdn, year,
  coalesce(sum(amount) FILTER (WHERE op_tea), 0)                                 AS operating_tea_def,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent), 0)            AS operating,
  coalesce(sum(amount) FILTER (WHERE op_tea AND is_ssa_agent), 0)                AS ssa_agent_operating,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'instruction'), 0)                AS op_instruction,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'instructional_support'), 0)      AS op_instructional_support,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'school_leadership'), 0)          AS op_school_leadership,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'student_support'), 0)            AS op_student_support,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'transportation'), 0)             AS op_transportation,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'food_service'), 0)               AS op_food_service,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'extracurricular'), 0)            AS op_extracurricular,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'general_administration'), 0)     AS op_general_administration,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'plant_maintenance_security'), 0) AS op_plant_maintenance_security,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'data_processing'), 0)            AS op_data_processing,
  coalesce(sum(amount) FILTER (WHERE op_tea AND NOT is_ssa_agent AND function_group = 'community_services'), 0)         AS op_community_services,
  coalesce(sum(amount) FILTER (WHERE object_series = '6500'), 0)                 AS debt_service,
  coalesce(sum(amount) FILTER (WHERE function = '81' OR object_series = '6600'), 0) AS capital,
  coalesce(sum(amount) FILTER (WHERE function = '91'), 0)                        AS recapture_fn91,
  coalesce(sum(amount) FILTER (WHERE function IN ('93', '97', '99')), 0)          AS intergovernmental
FROM a
GROUP BY cdn, year;
