-- Function mix of operating spending for the 10 largest districts, latest year (share of operating)
SELECT district_name, enrollment,
       round(instruction_per_student_real / op_per_student_real, 3) AS instruction,
       round(school_leadership_per_student_real / op_per_student_real, 3) AS leadership,
       round(plant_maintenance_security_per_student_real / op_per_student_real, 3) AS plant_security,
       round(general_administration_per_student_real / op_per_student_real, 3) AS general_admin
FROM mart_district_year WHERE year = (SELECT max(year) FROM mart_district_year) AND is_current
ORDER BY enrollment DESC LIMIT 10;
