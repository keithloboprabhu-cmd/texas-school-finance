-- Recapture paid by ESC region and by locale ($year)
SELECT 'ESC region ' || esc_region AS grp, 'region' AS kind, sum(recapture_paid) AS paid, count(*) FILTER (WHERE recapture_paid > 0) AS payers
FROM mart_recapture WHERE year = $year GROUP BY esc_region
UNION ALL
SELECT locale, 'locale', sum(recapture_paid), count(*) FILTER (WHERE recapture_paid > 0)
FROM mart_recapture WHERE year = $year GROUP BY locale
ORDER BY kind, paid DESC;
