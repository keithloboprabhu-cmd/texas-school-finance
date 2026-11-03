-- Recapture amounts TEA reports for years after the latest PEIMS year (near-final / preliminary)
SELECT year, amount_status, count(*) FILTER (WHERE recapture_paid > 0) AS payers, sum(recapture_paid) AS recapture_paid
FROM mart_recapture_recent GROUP BY ALL ORDER BY year;
