-- Enrollment-weighted average M&O and I&S tax rates by school year
SELECT year, round(mo_rate_wavg, 4) AS mo_rate, round(is_rate_wavg, 4) AS is_rate,
       round(is_rate_wavg / (mo_rate_wavg + is_rate_wavg), 3) AS is_share
FROM mart_tax_rates_state_year WHERE mo_rate_wavg IS NOT NULL ORDER BY year;
