-- Average adopted tax rates by school year: M&O vs I&S (enrollment-weighted)
SELECT year, mo_rate_wavg, is_rate_wavg, mo_rate_avg, is_rate_avg, n_districts
FROM mart_tax_rates_state_year WHERE mo_rate_wavg IS NOT NULL ORDER BY year;
