-- Open-enrollment charters, reported separately (no boundaries, no local property tax base).
-- Uses TEA's own operating total from the summarized file (charter single files not ingested).
CREATE OR REPLACE TABLE mart_charters_state_year AS
SELECT p.year, count(*) AS n_charters, sum(p.enrollment) AS enrollment,
       sum(p.tea_operating_total) AS operating_tea_def,
       sum(p.tea_operating_total) / nullif(sum(p.enrollment), 0) AS op_per_student_nominal
FROM stg_peims_summarized p JOIN dim_district d USING (cdn)
WHERE d.is_charter
GROUP BY p.year;
