-- Fall enrollment (PEIMS fall survey snapshot) as published in TEA's summarized actuals.
CREATE OR REPLACE TABLE fct_enrollment_district_year AS
SELECT cdn, year, enrollment FROM stg_peims_summarized;
