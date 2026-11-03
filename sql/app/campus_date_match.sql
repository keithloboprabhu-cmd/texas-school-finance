-- Share of new district (non-charter) campuses with an AskTED status date whose date falls within one
-- school year of the year the NCES ID first appears. A date from July of year Y-1 through June of year Y
-- counts as school year Y (the same labeling as first_year).
WITH c AS (
  SELECT first_year,
         year(strptime(askted_status_date, '%m/%d/%Y')) + (month(strptime(askted_status_date, '%m/%d/%Y')) >= 7)::INT AS askted_year
  FROM mart_campuses
  WHERE is_new AND is_charter = FALSE AND askted_status_date IS NOT NULL
)
SELECT count(*) AS n_dated, avg((abs(askted_year - first_year) <= 1)::INT) AS share_within_one_year FROM c;
