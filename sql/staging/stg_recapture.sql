-- TEA "Recapture Paid by District" (fiscal year = school year ending `year`).
CREATE OR REPLACE VIEW stg_recapture_paid AS
SELECT cdn, year::INTEGER AS year, recapture_paid, designated, amount_status
FROM read_parquet(getvariable('processed') || '/recapture_paid.parquet');

-- TEA Excess Local Revenue notification lists (2025-26, 2026-27).
CREATE OR REPLACE VIEW stg_elr_lists AS
SELECT * FROM read_parquet(getvariable('processed') || '/elr_lists.parquet');
