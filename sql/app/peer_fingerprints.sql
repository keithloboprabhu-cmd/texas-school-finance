-- Function shares of operating spending (latest year) for $cdn and its peers, with state median shares
WITH y AS (SELECT * FROM mart_district_year WHERE year = (SELECT max(year) FROM mart_district_year) AND is_current),
ids AS (SELECT $cdn AS cdn UNION ALL SELECT peer_cdn FROM mart_peers WHERE cdn = $cdn),
long AS (
  UNPIVOT y ON instruction_per_student_real, school_leadership_per_student_real, student_support_per_student_real,
     transportation_per_student_real, food_service_per_student_real, extracurricular_per_student_real,
     general_administration_per_student_real, plant_maintenance_security_per_student_real
  INTO NAME fn VALUE per_student
), sh AS (SELECT cdn, district_name, fn, per_student / nullif(op_per_student_real, 0) AS share FROM long),
med AS (SELECT fn, median(share) AS state_share FROM sh GROUP BY fn)
SELECT sh.cdn, sh.district_name, replace(replace(sh.fn, '_per_student_real', ''), '_', ' ') AS petal,
       sh.share, med.state_share, sh.share / nullif(med.state_share, 0) AS ratio
FROM sh JOIN med USING (fn) WHERE sh.cdn IN (SELECT cdn FROM ids);
