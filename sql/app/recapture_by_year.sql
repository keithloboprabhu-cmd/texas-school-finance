-- Statewide recapture paid by school year (TEA "Recapture Paid by District"), nominal and real
SELECT year, sum(recapture_paid) AS recapture_paid, sum(recapture_paid * real_factor) AS recapture_real,
       count(*) FILTER (WHERE recapture_paid > 0) AS payers
FROM mart_district_year GROUP BY year ORDER BY year;
