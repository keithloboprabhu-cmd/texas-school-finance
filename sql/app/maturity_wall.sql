-- Outstanding debt service by FINAL maturity year (latest fiscal year), refunding vs new money
SELECT final_maturity_year, purpose_group, n_issuances, principal_outstanding, debt_service_outstanding, as_of_fiscal_year
FROM mart_maturity_wall ORDER BY final_maturity_year, purpose_group;
