-- Finding 02: who spends far more than the controlled model predicts (latest year)
SELECT direction, count(*) AS n,
       count(*) FILTER (WHERE small_district) AS n_small,
       count(*) FILTER (WHERE locale = 'Rural') AS n_rural,
       median(enrollment) AS median_enrollment,
       median(op_per_student_real) AS median_actual,
       median(predicted_real) AS median_predicted,
       (SELECT avg(small_district::INT) FROM mart_outliers_latest) AS share_small_statewide,
       any_value(year) AS year
FROM mart_outliers_latest
WHERE direction IS NOT NULL
GROUP BY direction;
