-- TEA AskTED directory: one row per campus; district attributes repeat on every row.
CREATE OR REPLACE VIEW stg_askted AS
SELECT * FROM read_parquet(getvariable('processed') || '/askted.parquet');

CREATE OR REPLACE VIEW stg_ccd_lea AS
SELECT * FROM read_parquet(getvariable('processed') || '/ccd_lea.parquet');

CREATE OR REPLACE VIEW stg_edge_lea AS
SELECT * FROM read_parquet(getvariable('processed') || '/edge_lea.parquet');

CREATE OR REPLACE VIEW stg_boundaries AS
SELECT geoid, boundary_name, sd_type, aland, awater, int_lat, int_lon
FROM read_parquet(getvariable('processed') || '/boundaries.parquet');
