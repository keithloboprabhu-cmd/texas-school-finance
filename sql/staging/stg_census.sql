CREATE OR REPLACE VIEW stg_saipe AS
SELECT * FROM read_parquet(getvariable('processed') || '/saipe.parquet');

CREATE OR REPLACE VIEW stg_acs AS
SELECT * FROM read_parquet(getvariable('processed') || '/acs.parquet');

CREATE OR REPLACE VIEW stg_cpi AS
SELECT year::INTEGER AS year, cpi FROM read_parquet(getvariable('processed') || '/cpi_school_year.parquet');
