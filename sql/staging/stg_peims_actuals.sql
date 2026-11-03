-- PEIMS single-file district actuals, aggregated by the ingest step to
-- (cdn, year, fund, function, object_series). Expenditure objects only (6100-6600).
CREATE OR REPLACE VIEW stg_peims_actuals AS
SELECT a.cdn, a.year::INTEGER AS year, a.fund, fund_group(a.fund) AS fund_group,
       a.function, a.object_series, a.amount
FROM read_parquet(getvariable('processed') || '/peims_actuals/*.parquet') a
WHERE a.object_series BETWEEN '6100' AND '6600';
