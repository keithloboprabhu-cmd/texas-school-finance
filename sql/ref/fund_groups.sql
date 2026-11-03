-- PEIMS fund code ranges. Source: FASRG Update 20, Module 1 FAR Appendices, fund code section
-- (Special revenue categories page; 599 Debt Service Funds; 699 Capital Projects Funds).
-- TEA's operating totals exclude capital projects funds (6xx): confirmed against the PEIMS
-- summarized actuals in tests/test_definitions.py.
CREATE OR REPLACE MACRO fund_group(f) AS CASE
  WHEN f BETWEEN '100' AND '199' THEN 'general'
  WHEN f BETWEEN '200' AND '289' THEN 'special_revenue_federal'
  WHEN f BETWEEN '291' AND '379' THEN 'ssa_fiscal_agent_federal'
  WHEN f BETWEEN '381' AND '429' THEN 'special_revenue_state'
  WHEN f BETWEEN '431' AND '459' THEN 'ssa_fiscal_agent_state_local'
  WHEN f BETWEEN '461' AND '499' THEN 'special_revenue_local'
  WHEN f BETWEEN '500' AND '599' THEN 'debt_service'
  WHEN f BETWEEN '600' AND '699' THEN 'capital_projects'
  ELSE 'proprietary_or_fiduciary'
END;
