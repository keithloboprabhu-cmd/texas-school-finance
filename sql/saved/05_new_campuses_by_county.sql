-- Campuses opened in 2016-17 or later that are still open, by county
SELECT county, count(*) AS new_campuses, count(*) FILTER (WHERE is_charter) AS charter
FROM mart_campuses WHERE is_new AND is_open AND county IS NOT NULL
GROUP BY county ORDER BY new_campuses DESC LIMIT 20;
