-- Debt per student next to property wealth per student, latest Bond Review Board year
SELECT district_name, round(debt_per_student) AS debt_per_student, round(wealth_per_student_real) AS wealth_per_student,
       is_rate, cab_share_principal
FROM mart_debt_district WHERE debt_per_student IS NOT NULL ORDER BY debt_per_student DESC LIMIT 25;
