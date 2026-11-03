-- Each current district's statewide rank of real spending per student: first year vs latest year
WITH r AS (
  SELECT y.cdn, y.district_name, y.year, y.enrollment,
         rank() OVER (PARTITION BY y.year ORDER BY y.op_per_student_real DESC) AS spend_rank
  FROM mart_district_year y JOIN mart_districts d USING (cdn)
  WHERE y.is_current AND y.enrollment > 0 AND y.operating > 0 AND y.op_per_student_real IS NOT NULL AND NOT d.enrollment_caution
)
SELECT a.cdn, a.district_name, a.spend_rank AS rank_first, b.spend_rank AS rank_latest, b.enrollment,
       a.year AS first_year, b.year AS latest_year
FROM r a JOIN r b USING (cdn)
WHERE a.year = (SELECT min(year) FROM r) AND b.year = (SELECT max(year) FROM r);
