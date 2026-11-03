-- Top 10 recapture districts per student, latest school year (real dollars)
SELECT district_name, county, enrollment, recapture_paid, round(recapture_per_student_real) AS recapture_per_student
FROM mart_recapture WHERE year = (SELECT max(year) FROM mart_recapture) AND recapture_paid > 0
ORDER BY recapture_per_student_real DESC LIMIT 10;
