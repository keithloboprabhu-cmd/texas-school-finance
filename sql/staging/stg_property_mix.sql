CREATE OR REPLACE VIEW stg_property_mix AS
SELECT * FROM read_parquet(getvariable('processed') || '/property_mix.parquet');
