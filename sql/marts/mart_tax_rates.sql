-- Adopted M&O and I&S tax rates (per $100 of taxable value), 2005-06 onward.
CREATE OR REPLACE TABLE mart_tax_rates AS
SELECT t.cdn, t.year, d.district_name, t.mo_rate, t.is_rate, t.mo_rate + t.is_rate AS total_rate,
       t.is_rate / nullif(t.mo_rate + t.is_rate, 0) AS is_share
FROM stg_tax_rates t JOIN dim_district d USING (cdn)
WHERE d.in_analysis;

-- Statewide: simple and enrollment-weighted average rates per year
CREATE OR REPLACE TABLE mart_tax_rates_state_year AS
SELECT t.year,
  avg(t.mo_rate) AS mo_rate_avg, avg(t.is_rate) AS is_rate_avg,
  sum(t.mo_rate * e.enrollment) / sum(e.enrollment) FILTER (WHERE t.mo_rate IS NOT NULL) AS mo_rate_wavg,
  sum(t.is_rate * e.enrollment) / sum(e.enrollment) FILTER (WHERE t.is_rate IS NOT NULL) AS is_rate_wavg,
  count(*) AS n_districts
FROM mart_tax_rates t LEFT JOIN fct_enrollment_district_year e USING (cdn, year)
GROUP BY t.year;
