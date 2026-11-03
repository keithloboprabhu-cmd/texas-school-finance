-- District debt (BRB). Fiscal year = Texas state fiscal year (Sept-Aug) ending in `fiscal_year`.
CREATE OR REPLACE TABLE mart_debt_district_year AS
WITH iss AS (
  SELECT cdn, fiscal_year,
    sum(principal_outstanding) FILTER (WHERE pledgetype = 'GO')     AS tax_supported_principal,
    sum(debt_service_outstanding) FILTER (WHERE pledgetype = 'GO')  AS tax_supported_debt_service,
    sum(principal_outstanding) FILTER (WHERE pledgetype <> 'GO')    AS other_principal,
    sum(principal_outstanding)                                      AS total_principal,
    sum(debt_service_outstanding)                                   AS total_debt_service,
    max(ada) AS ada, max(wealth_per_ada) AS wealth_per_ada, max(taxrateis) AS brb_is_rate,
    count(*) AS n_issuances
  FROM stg_brb_issuance GROUP BY ALL
)
SELECT i.*, d.district_name, d.county, d.esc_region, d.locale,
       i.tax_supported_principal / nullif(i.ada, 0) AS debt_per_ada,
       c.cab_principal, c.cib_principal, c.cab_interest, c.cib_interest,
       c.cab_principal / nullif(c.cab_principal + c.cib_principal, 0) AS cab_share_principal
FROM iss i JOIN dim_district d USING (cdn)
LEFT JOIN stg_brb_cab_cib c USING (cdn, fiscal_year)
WHERE d.in_analysis;

-- Latest fiscal year per district, with property wealth, tax rates and enrollment for context
CREATE OR REPLACE TABLE mart_debt_district AS
SELECT y.*, m.enrollment, m.wealth_per_student_real, m.is_rate, m.mo_rate,
       y.tax_supported_principal / nullif(m.enrollment, 0) AS debt_per_student,
       dd.lat, dd.lon
FROM mart_debt_district_year y
JOIN mart_districts dd USING (cdn)
LEFT JOIN mart_district_year m ON m.cdn = y.cdn AND m.year = (SELECT max(year) FROM mart_district_year)
WHERE y.fiscal_year = (SELECT max(fiscal_year) FROM stg_brb_issuance);

-- Statewide debt by fiscal year
CREATE OR REPLACE TABLE mart_debt_state_year AS
SELECT fiscal_year, count(*) AS n_districts,
       sum(tax_supported_principal) AS tax_supported_principal, sum(total_principal) AS total_principal,
       sum(total_debt_service) AS total_debt_service,
       sum(cab_principal) AS cab_principal, sum(cib_principal) AS cib_principal,
       sum(cab_interest) AS cab_interest, sum(cib_interest) AS cib_interest
FROM mart_debt_district_year GROUP BY fiscal_year;

-- "Maturity wall": outstanding debt service in the latest fiscal year, grouped by each issuance's
-- FINAL maturity year. BRB does not publish per-issuance annual payment schedules in bulk, so this
-- shows when debt finishes, not an annual payment projection. Split: refunding vs. new money.
CREATE OR REPLACE TABLE mart_maturity_wall AS
SELECT year(i.maturitydate) AS final_maturity_year,
       CASE WHEN i.issuepurpose = 'Refund' THEN 'Refunding' ELSE 'New money' END AS purpose_group,
       count(*) AS n_issuances,
       sum(i.principal_outstanding) AS principal_outstanding,
       sum(i.debt_service_outstanding) AS debt_service_outstanding,
       any_value(i.fiscal_year) AS as_of_fiscal_year
FROM stg_brb_issuance i JOIN dim_district d USING (cdn)
WHERE d.in_analysis AND i.fiscal_year = (SELECT max(fiscal_year) FROM stg_brb_issuance)
GROUP BY ALL;
