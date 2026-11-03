-- Property wealth by school year. Convention: school year ending Y uses tax year Y-1 values,
-- i.e. the taxable value the district levies on during that school year (school year 2024-25 ->
-- tax year 2024). TEA's own funding lag differs by era (before 2019-20 funding used prior-year
-- values; see the CPTD file headers) and is documented on the Methodology page.
CREATE OR REPLACE TABLE fct_wealth_district_year AS
SELECT v.cdn, v.tax_year + 1 AS year, v.tax_year, v.value_assigned AS property_value, v.value_source
FROM stg_property_values v;
