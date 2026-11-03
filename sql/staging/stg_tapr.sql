-- TEA TAPR district profile (2023-24): student counts and shares.
CREATE OR REPLACE VIEW stg_tapr AS
SELECT * FROM read_parquet(getvariable('processed') || '/tapr.parquet');
