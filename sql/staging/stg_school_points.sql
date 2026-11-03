-- NCES EDGE public school locations by school year (2015-16 = 2016 ... 2024-25 = 2025), Texas.
CREATE OR REPLACE VIEW stg_school_points AS
SELECT * FROM read_parquet(getvariable('processed') || '/school_points.parquet');
