-- Recapture by district and year (analysis universe), with TEA's 2025-26 and 2026-27
-- excess local revenue list columns where available.
CREATE OR REPLACE TABLE mart_recapture AS
SELECT m.cdn, m.year, m.district_name, m.county, m.esc_region, m.locale, m.enrollment,
       m.recapture_paid, m.recapture_per_student_real, m.recapture_designated, rp.amount_status,
       m.recapture_fn91, m.operating,
       m.recapture_paid / nullif(m.operating + m.recapture_paid, 0) AS recapture_share_of_operating_plus_recapture
FROM mart_district_year m
LEFT JOIN stg_recapture_paid rp USING (cdn, year);

-- Recapture amounts reported for school years after the last PEIMS year (near-final/preliminary)
CREATE OR REPLACE TABLE mart_recapture_recent AS
SELECT rp.cdn, d.district_name, rp.year, rp.recapture_paid, rp.amount_status
FROM stg_recapture_paid rp JOIN dim_district d USING (cdn)
WHERE d.in_analysis AND rp.year > (SELECT max(year) FROM fct_spending_district_year);

CREATE OR REPLACE TABLE mart_elr_list AS
SELECT e.*, d.county, d.esc_region, d.locale, d.int_lat AS lat, d.int_lon AS lon
FROM stg_elr_lists e LEFT JOIN dim_district d USING (cdn);
