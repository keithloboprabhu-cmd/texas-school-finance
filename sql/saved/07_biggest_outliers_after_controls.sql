-- Districts that spend furthest above or below the model's prediction, latest year
SELECT direction, district_name, enrollment, round(op_per_student_real) AS actual, round(predicted_real) AS predicted,
       round(std_residual, 2) AS std_residual, hint
FROM mart_outliers_latest WHERE direction IS NOT NULL ORDER BY std_residual DESC;
