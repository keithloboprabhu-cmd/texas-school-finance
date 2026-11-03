-- Latest fiscal year debt by district (BRB), with wealth, I&S rate and location
SELECT cdn, district_name, county, esc_region, locale, fiscal_year, lat, lon, enrollment, ada,
       tax_supported_principal, total_debt_service, debt_per_ada, debt_per_student, wealth_per_ada,
       wealth_per_student_real, is_rate, mo_rate, cab_principal, cib_principal, cab_share_principal, n_issuances
FROM mart_debt_district ORDER BY tax_supported_principal DESC;
