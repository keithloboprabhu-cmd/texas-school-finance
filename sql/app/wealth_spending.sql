-- Wealth & Spending scatter for one school year ($year): current districts with enrollment, spending
-- and property wealth; districts flagged enrollment_caution are returned but marked (even when their
-- spending was removed as a data anomaly, so the page can count them).
SELECT y.cdn, y.district_name, y.county, y.locale, y.enrollment, y.small_district,
       y.op_per_student_real, y.wealth_per_student_real, y.recapture_paid,
       d.econ_disadv_pct, d.median_household_income, d.child_poverty_rate, d.enrollment_caution
FROM mart_district_year y JOIN mart_districts d USING (cdn)
WHERE y.year = $year AND y.is_current AND y.enrollment > 0 AND y.operating > 0 AND (y.op_per_student_real IS NOT NULL OR d.enrollment_caution)
  AND y.wealth_per_student_real > 0;
