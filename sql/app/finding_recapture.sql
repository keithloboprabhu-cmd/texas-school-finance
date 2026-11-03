-- Finding 03: recapture by property mix and household income ($year; property mix of tax year $year - 1).
-- The income median uses the same districts as the Wealth & Spending income chart
-- (not enrollment_caution, with spending, property wealth and Census income).
WITH y AS (
  SELECT m.cdn, m.recapture_paid, d.median_household_income AS income, p.mineral_share,
         NOT d.enrollment_caution AND m.enrollment > 0 AND m.op_per_student_real IS NOT NULL
           AND m.wealth_per_student_real > 0 AND d.median_household_income IS NOT NULL AS in_chart
  FROM mart_district_year m
  JOIN mart_districts d USING (cdn)
  LEFT JOIN mart_property_mix p ON p.cdn = m.cdn AND p.tax_year = $year - 1
  WHERE m.year = $year AND m.is_current
)
SELECT count(*) FILTER (WHERE recapture_paid > 0)                                   AS payers,
       sum(recapture_paid)                                                          AS total_paid,
       sum(recapture_paid) FILTER (WHERE mineral_share > 0.5)                       AS paid_by_mineral_majority,
       count(*) FILTER (WHERE recapture_paid > 0 AND mineral_share > 0.5)           AS payers_mineral_majority,
       count(*) FILTER (WHERE recapture_paid > 0
                          AND income < (SELECT median(income) FROM y WHERE in_chart))  AS payers_below_median_income
FROM y;
