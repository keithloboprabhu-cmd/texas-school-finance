-- Headline operating = TEA-definition operating minus SSA fiscal-agent funds, exactly; and the
-- TEA-definition total never includes recapture (fn 91), debt service (obj 6500) or capital (fn 81, obj 6600):
-- recomputed here from the staged codes.
WITH excluded AS (
  SELECT cdn, year, sum(amount) AS amt
  FROM stg_peims_actuals s JOIN ref_function_groups g USING (function) JOIN ref_object_groups o USING (object_series)
  WHERE g.in_operating AND o.is_operating_object AND s.fund_group <> 'capital_projects'
    AND (s.function IN ('81', '91') OR s.object_series IN ('6500', '6600'))
  GROUP BY ALL
)
SELECT f.cdn, f.year FROM fct_spending_district_year f LEFT JOIN excluded x USING (cdn, year)
WHERE abs(f.operating - (f.operating_tea_def - f.ssa_agent_operating)) > 1 OR coalesce(x.amt, 0) <> 0;
