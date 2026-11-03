-- Latest-year real spending per student by function group: district ($cdn), peer median and state shares
WITH y AS (SELECT * FROM mart_district_year WHERE year = (SELECT max(year) FROM mart_district_year) AND is_current),
long AS (
  UNPIVOT y ON instruction_per_student_real, instructional_support_per_student_real, school_leadership_per_student_real,
     student_support_per_student_real, transportation_per_student_real, food_service_per_student_real,
     extracurricular_per_student_real, general_administration_per_student_real,
     plant_maintenance_security_per_student_real, data_processing_per_student_real, community_services_per_student_real
  INTO NAME fn VALUE per_student
), shares AS (
  SELECT cdn, fn, per_student, per_student / nullif(op_per_student_real, 0) AS share FROM long
)
SELECT replace(replace(s.fn, '_per_student_real', ''), '_', ' ') AS function_group,
       max(s.per_student) FILTER (WHERE s.cdn = $cdn)                                    AS district,
       median(s.per_student) FILTER (WHERE s.cdn IN (SELECT peer_cdn FROM mart_peers WHERE cdn = $cdn)) AS peer_median,
       max(s.share) FILTER (WHERE s.cdn = $cdn)                                          AS district_share,
       median(s.share)                                                                   AS state_median_share
FROM shares s GROUP BY s.fn ORDER BY district DESC;
