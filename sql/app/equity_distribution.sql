-- District real operating spending per student by year, for the ridgeline (same universe as the metrics)
SELECT y.year, y.cdn, y.enrollment, y.op_per_student_real
FROM mart_district_year y LEFT JOIN mart_districts d USING (cdn)
WHERE y.enrollment > 0 AND y.operating > 0 AND y.op_per_student_real IS NOT NULL AND NOT coalesce(d.enrollment_caution, FALSE);
