-- TEA adopted tax rates (per $100 of value) by school year ending `year`.
-- Impossible values are removed (both rates set to NULL for that district-year): an M&O rate under
-- $0.30 or an I&S rate over $1.00. One case in the data: Canadian ISD 2009-10 (M&O 0.20, I&S 1.03,
-- against about 0.94 and 0.31 in the surrounding years).
CREATE OR REPLACE VIEW stg_tax_rates AS
SELECT cdn, year::INTEGER AS year,
       CASE WHEN mo_rate < 0.30 OR is_rate > 1.00 THEN NULL ELSE mo_rate END AS mo_rate,
       CASE WHEN mo_rate < 0.30 OR is_rate > 1.00 THEN NULL ELSE is_rate END AS is_rate
FROM read_parquet(getvariable('processed') || '/tax_rates.parquet');
