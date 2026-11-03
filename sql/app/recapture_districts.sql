-- Recapture by district for one school year ($year), with location for the flow map
SELECT r.cdn, r.district_name, r.county, r.esc_region, r.locale, r.enrollment,
       r.recapture_paid, r.recapture_per_student_real, r.recapture_share_of_operating_plus_recapture AS share_of_spending,
       r.recapture_fn91, d.lat, d.lon, d.median_household_income
FROM mart_recapture r JOIN mart_districts d USING (cdn)
WHERE r.year = $year AND r.recapture_paid > 0
ORDER BY r.recapture_paid DESC;
