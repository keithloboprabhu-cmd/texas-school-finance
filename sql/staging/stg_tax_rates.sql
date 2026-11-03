-- TEA adopted tax rates (per $100 of value) by school year ending `year`.
CREATE OR REPLACE VIEW stg_tax_rates AS
SELECT cdn, year::INTEGER AS year, mo_rate, is_rate
FROM read_parquet(getvariable('processed') || '/tax_rates.parquet');
