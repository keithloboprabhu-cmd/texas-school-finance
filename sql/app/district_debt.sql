-- Debt outstanding for $cdn by state fiscal year (BRB)
SELECT fiscal_year, tax_supported_principal, total_debt_service, cab_principal, cib_principal, debt_per_ada, ada
FROM mart_debt_district_year WHERE cdn = $cdn ORDER BY fiscal_year;
