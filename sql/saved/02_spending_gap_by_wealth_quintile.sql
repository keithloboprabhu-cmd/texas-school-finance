-- Real operating spending per student by property-wealth quintile (district quintiles, enrollment-weighted means)
WITH y AS (
  SELECT *, ntile(5) OVER (ORDER BY wealth_per_student_real) AS wealth_quintile
  FROM mart_district_year WHERE year = (SELECT max(year) FROM mart_district_year) AND is_current
    AND enrollment > 0 AND wealth_per_student_real > 0)
SELECT wealth_quintile, count(*) AS districts, sum(enrollment) AS students,
       round(sum(op_per_student_real * enrollment) / sum(enrollment)) AS spend_per_student
FROM y GROUP BY 1 ORDER BY 1;
