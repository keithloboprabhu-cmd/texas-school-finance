-- Statewide operating total (TEA definition) within +/-2% of TEA's own published totals, every year.
SELECT s.year, sum(f.operating_tea_def) AS ours, sum(s.tea_operating_total) AS tea
FROM stg_peims_summarized s JOIN fct_spending_district_year f USING (cdn, year)
GROUP BY 1 HAVING abs(sum(f.operating_tea_def) / sum(s.tea_operating_total) - 1) > 0.02;
