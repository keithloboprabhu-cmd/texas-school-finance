-- Adopted M&O and I&S tax rates for $cdn by school year
SELECT year, mo_rate, is_rate, total_rate FROM mart_tax_rates WHERE cdn = $cdn ORDER BY year;
