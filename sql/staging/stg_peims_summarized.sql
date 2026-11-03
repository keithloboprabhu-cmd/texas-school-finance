-- TEA PEIMS summarized actuals (one row per district incl. charters, per school year).
-- Column names are TEA's; "ALL FUNDS-" = all funds, "GEN FUNDS-" = general fund.
CREATE OR REPLACE VIEW stg_peims_summarized AS
SELECT cdn, year::INTEGER AS year, district_name,
  "FALL SURVEY ENROLLMENT"                            AS enrollment,
  "ALL FUNDS-LOCAL TAX REVENUE FROM M&O"              AS rev_local_mo_tax,
  "ALL FUNDS-LOCAL PROPERTY TAXES FROM I&S"           AS rev_local_is_tax,
  "ALL FUNDS-OTHER LOCAL & INTERMEDIATE REVENUE"      AS rev_other_local,
  "ALL FUNDS-STATE REVENUE"                           AS rev_state,
  "ALL FUNDS-STATE DEBT FUNDS"                        AS rev_state_debt,
  "ALL FUNDS-FEDERAL REVENUE"                         AS rev_federal,
  "ALL FUNDS-TOTAL OPER EXPENDITURES FOR TD"          AS tea_operating_total,
  "ALL FUNDS-EQUITY TRANSFERS FOR TD"                 AS tea_equity_transfers,
  "ALL FUNDS-INTERGOVERN CHARGES EXPEND"              AS tea_intergovernmental,
  "ALL FUNDS-DEBT SERVICE (OBJECT 6500) FOR TD"       AS tea_debt_service_obj,
  "ALL FUNDS-CAPITAL PROJECTS(OBJECT 6600) FOR TD"    AS tea_capital_outlay_obj,
  "ALL FUNDS-TOTAL DISBURSEMENTS"                     AS tea_total_disbursements
FROM read_parquet(getvariable('processed') || '/peims_summarized.parquet');
