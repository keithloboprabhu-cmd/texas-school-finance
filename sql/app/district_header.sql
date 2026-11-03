-- Profile header and key metrics for one district ($cdn), latest year, with state medians
WITH y AS (SELECT * FROM mart_district_year WHERE year = (SELECT max(year) FROM mart_district_year) AND is_current),
st AS (SELECT median(op_per_student_real) AS st_spend, median(wealth_per_student_real) AS st_wealth FROM y),
sd AS (SELECT median(median_household_income) AS st_income, median(child_poverty_rate) AS st_poverty,
              median(econ_disadv_pct) AS st_econ FROM mart_districts)
SELECT d.*, y.year, y.enrollment, y.small_district, y.op_per_student_real, y.wealth_per_student_real,
       y.recapture_paid, y.recapture_designated, y.mo_rate, y.is_rate, y.share_local, y.share_state, y.share_federal,
       st.st_spend, st.st_wealth, sd.st_income, sd.st_poverty, sd.st_econ,
       o.predicted_real, o.std_residual, debt.tax_supported_principal, debt.debt_per_student, debt.cab_share_principal,
       debt.fiscal_year AS debt_fy, g.growth_5y, g.growth_10y, g.new_campuses_since_2016_17
FROM mart_districts d
JOIN y ON y.cdn = d.cdn
CROSS JOIN st
CROSS JOIN sd
LEFT JOIN mart_outliers_latest o ON o.cdn = d.cdn
LEFT JOIN mart_debt_district debt ON debt.cdn = d.cdn
LEFT JOIN mart_growth_capital g ON g.cdn = d.cdn
WHERE d.cdn = $cdn;
