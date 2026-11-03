-- Statewide equity measures by school year
SELECT year, round(mean_spend) AS mean_spend, round(cv_bounded, 3) AS cv, round(mcloone, 3) AS mcloone,
       round(restricted_range_ratio, 3) AS range_95_5, round(elasticity, 3) AS elasticity, round(quintile_gap_ratio, 3) AS quintile_gap
FROM mart_equity_state_year ORDER BY year;
