-- PEIMS function codes -> analysis groups.
-- Source for every code and title: TEA Financial Accountability System Resource Guide (FASRG),
-- Update 20, Module 1 FAR Appendices, function code section
-- https://tea.texas.gov/data-reports/financial-accountability/fasrg/fasrg20-module1-farappendices.pdf
-- `in_operating` reproduces TEA's "TOTAL OPER EXPENDITURES" in the PEIMS summarized actuals
-- (checked by tests/test_definitions.py against every year, 2009-2025).
CREATE OR REPLACE TABLE ref_function_groups AS
SELECT * FROM (VALUES
  ('11', 'Instruction',                                   'instruction',              TRUE),
  ('12', 'Instructional Resources and Media Services',    'instructional_support',    TRUE),
  ('13', 'Curriculum and Instructional Staff Development','instructional_support',    TRUE),
  ('21', 'Instructional Leadership',                      'school_leadership',        TRUE),
  ('23', 'School Leadership',                             'school_leadership',        TRUE),
  ('31', 'Guidance, Counseling, and Evaluation Services', 'student_support',          TRUE),
  ('32', 'Social Work Services',                          'student_support',          TRUE),
  ('33', 'Health Services',                               'student_support',          TRUE),
  ('34', 'Student (Pupil) Transportation',                'transportation',           TRUE),
  ('35', 'Food Services',                                 'food_service',             TRUE),
  ('36', 'Extracurricular Activities',                    'extracurricular',          TRUE),
  ('41', 'General Administration',                        'general_administration',   TRUE),
  ('51', 'Facilities Maintenance and Operations',         'plant_maintenance_security', TRUE),
  ('52', 'Security and Monitoring Services',              'plant_maintenance_security', TRUE),
  ('53', 'Data Processing Services',                      'data_processing',          TRUE),
  ('61', 'Community Services',                            'community_services',       TRUE),
  ('71', 'Debt Service',                                  'debt_service',             FALSE),
  ('81', 'Facilities Acquisition and Construction',       'capital',                  FALSE),
  ('91', 'Purchase of WADA to Reduce Excess Local Revenue (recapture)', 'recapture',  FALSE),
  -- 92 is not defined in FASRG Update 20 (unverified). TEA's summarized file reports it together
  -- with function 41 ("GENERAL ADMINISTRAT EXPEND-FCT41,92"), so it is grouped with 41 here.
  ('92', 'Not defined in FASRG Update 20 (unverified); reported with function 41 by TEA', 'general_administration', TRUE),
  ('93', 'Payments to Fiscal Agent or Member Districts of Shared Services Arrangements', 'intergovernmental', FALSE),
  -- 95 is an intergovernmental charge, but TEA counts it as operating and reports it with
  -- instruction ("INSTRUCTION + TRANSFER EXPEND-FCT11,95"); this project follows TEA.
  ('95', 'Payments to Juvenile Justice Alternative Education Programs', 'instruction', TRUE),
  ('97', 'Payments to Tax Increment Fund',                'intergovernmental',        FALSE),
  ('99', 'Other Intergovernmental Charges',               'intergovernmental',        FALSE)
) AS t(function, function_title, function_group, in_operating);
