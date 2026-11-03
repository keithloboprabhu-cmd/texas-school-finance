-- The 10 most similar districts to $cdn (standardized size, property wealth and need), latest year
SELECT p.peer_rank, p.peer_cdn AS cdn, y.district_name, y.county, y.enrollment, round(y.wealth_per_student_real) AS wealth_per_student_real,
       d.econ_disadv_pct, round(y.op_per_student_real) AS op_per_student_real, round(y.recapture_paid) AS recapture_paid
FROM mart_peers p
JOIN mart_district_year y ON y.cdn = p.peer_cdn AND y.year = (SELECT max(year) FROM mart_district_year)
JOIN mart_districts d ON d.cdn = p.peer_cdn
WHERE p.cdn = $cdn ORDER BY p.peer_rank;
