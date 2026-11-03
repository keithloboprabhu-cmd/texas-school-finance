-- Real operating spending per student for $cdn, the state median and the peer interquartile band, by year
WITH p AS (SELECT peer_cdn FROM mart_peers WHERE cdn = $cdn)
SELECT y.year,
       max(y.op_per_student_real) FILTER (WHERE y.cdn = $cdn)                   AS district,
       median(y.op_per_student_real) FILTER (WHERE y.is_current)                AS state_median,
       quantile_cont(y.op_per_student_real, 0.25) FILTER (WHERE y.cdn IN (SELECT peer_cdn FROM p)) AS peer_p25,
       quantile_cont(y.op_per_student_real, 0.75) FILTER (WHERE y.cdn IN (SELECT peer_cdn FROM p)) AS peer_p75,
       max(y.enrollment) FILTER (WHERE y.cdn = $cdn)                            AS enrollment
FROM mart_district_year y GROUP BY y.year ORDER BY y.year;
