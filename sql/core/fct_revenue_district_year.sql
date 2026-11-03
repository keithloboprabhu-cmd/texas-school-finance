-- Revenue by source (all funds), from TEA's PEIMS summarized actuals.
-- local = M&O tax + I&S tax + other local & intermediate; state = state revenue + state debt funds.
CREATE OR REPLACE TABLE fct_revenue_district_year AS
SELECT cdn, year,
  rev_local_mo_tax, rev_local_is_tax, rev_other_local,
  rev_local_mo_tax + rev_local_is_tax + rev_other_local AS rev_local,
  rev_state + rev_state_debt                             AS rev_state,
  rev_federal,
  rev_local_mo_tax + rev_local_is_tax + rev_other_local + rev_state + rev_state_debt + rev_federal AS rev_total
FROM stg_peims_summarized;
