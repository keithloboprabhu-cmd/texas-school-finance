-- Certified property value "used for school funding" (TEA PTAD Tax Final), by tax year.
-- TEA's tax year 2022 file lists 966 districts; missing districts are filled from the
-- Comptroller PVS 2022 worksheet export (ASGN T2), which equals TEA's value for 98-100% of
-- districts in the years where both exist (2022-2025).
CREATE OR REPLACE VIEW stg_property_values AS
WITH tea AS (
  SELECT cdn, tax_year, value_assigned, 'TEA PTAD Tax Final' AS value_source
  FROM read_parquet(getvariable('processed') || '/property_values.parquet')
  WHERE value_assigned IS NOT NULL
), pvs_fill AS (
  SELECT p.cdn, p.tax_year, p.value_t2_pvs AS value_assigned, 'Comptroller PVS (ASGN T2)' AS value_source
  FROM read_parquet(getvariable('processed') || '/property_mix.parquet') p
  ANTI JOIN tea USING (cdn, tax_year)
)
SELECT * FROM tea UNION ALL SELECT * FROM pvs_fill;
