-- Every Atlas map layer for one school year ($year). Debt, growth, need and model residuals are
-- latest-available snapshots (see each layer's note); property mix uses the tax year that funds $year
-- when available, otherwise the latest tax year.
WITH y AS (
  SELECT * FROM mart_district_year WHERE year = $year AND is_current
), mix AS (
  SELECT cdn, arg_max(mineral_share, tax_year) AS mineral_share
  FROM mart_property_mix WHERE tax_year <= $year - 1 OR tax_year = (SELECT min(tax_year) FROM mart_property_mix)
  GROUP BY cdn
)
SELECT d.cdn, d.geoid, d.district_name, d.county, d.esc_region, d.locale, d.lat, d.lon,
       y.enrollment, y.small_district,
       y.wealth_per_student_real AS wealth_per_student, d.median_household_income, mix.mineral_share,
       y.op_per_student_real AS op_per_student, o.std_residual,
       y.recapture_per_student_real AS recapture_per_student, y.recapture_paid,
       debt.debt_per_student, y.is_rate, y.mo_rate, debt.cab_share_principal AS cab_share,
       g.growth_5y, g.growth_10y, g.new_campuses_since_2016_17 AS new_campuses,
       d.child_poverty_rate, d.econ_disadv_pct
FROM mart_districts d
LEFT JOIN y USING (cdn)
LEFT JOIN mix USING (cdn)
LEFT JOIN mart_outliers_latest o USING (cdn)
LEFT JOIN mart_debt_district debt USING (cdn)
LEFT JOIN mart_growth_capital g USING (cdn);
