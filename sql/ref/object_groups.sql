-- PEIMS expenditure object series (first two digits of the 4-digit object code).
-- Source: FASRG Update 20, Module 1 FAR Appendices, object code section.
-- Operating spending uses 6100-6400 only (TEA's "TOTAL OPERATING EXPENDITURES BY OBJ").
CREATE OR REPLACE TABLE ref_object_groups AS
SELECT * FROM (VALUES
  ('6100', 'Payroll Costs',                          'operating',    TRUE),
  ('6200', 'Professional and Contracted Services',   'operating',    TRUE),
  ('6300', 'Supplies and Materials',                 'operating',    TRUE),
  ('6400', 'Other Operating Expenses',               'operating',    TRUE),
  ('6500', 'Debt Service',                           'debt_service', FALSE),
  ('6600', 'Capital Outlay - Land, Buildings, and Equipment', 'capital', FALSE)
) AS t(object_series, object_title, object_group, is_operating_object);
