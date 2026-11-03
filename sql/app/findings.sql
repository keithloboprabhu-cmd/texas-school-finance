-- Atlas findings strip: statewide equity in the first and latest years with property-wealth data.
SELECT year, elasticity, elasticity_lo, elasticity_hi, wealth_spend_corr, mean_spend, median_spend,
       quintile_gap_ratio, quintile_gap_dollars, mcloone, restricted_range_ratio, n_districts, students
FROM mart_equity_state_year
WHERE elasticity IS NOT NULL
ORDER BY year;
