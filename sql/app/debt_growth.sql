-- Debt per student (latest FY) vs 5-year enrollment growth
SELECT d.cdn, d.district_name, d.debt_per_student, d.tax_supported_principal, g.growth_5y, g.enroll_now,
       d.wealth_per_student_real, g.enrollment_caution
FROM mart_debt_district d JOIN mart_growth_capital g USING (cdn)
WHERE d.debt_per_student IS NOT NULL AND g.growth_5y IS NOT NULL AND g.enroll_5y_ago >= 100;
