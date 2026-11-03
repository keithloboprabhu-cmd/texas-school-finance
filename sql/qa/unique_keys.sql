-- Every mart has a unique key; returns offending tables.
SELECT 'mart_district_year' AS mart, count(*) - count(DISTINCT (cdn, year)) AS dupes FROM mart_district_year HAVING dupes > 0
UNION ALL SELECT 'mart_districts', count(*) - count(DISTINCT cdn) FROM mart_districts HAVING count(*) - count(DISTINCT cdn) > 0
UNION ALL SELECT 'mart_recapture', count(*) - count(DISTINCT (cdn, year)) FROM mart_recapture HAVING count(*) - count(DISTINCT (cdn, year)) > 0
UNION ALL SELECT 'mart_tax_rates', count(*) - count(DISTINCT (cdn, year)) FROM mart_tax_rates HAVING count(*) - count(DISTINCT (cdn, year)) > 0
UNION ALL SELECT 'mart_property_mix', count(*) - count(DISTINCT (cdn, tax_year)) FROM mart_property_mix HAVING count(*) - count(DISTINCT (cdn, tax_year)) > 0
UNION ALL SELECT 'mart_equity_state_year', count(*) - count(DISTINCT year) FROM mart_equity_state_year HAVING count(*) - count(DISTINCT year) > 0;
