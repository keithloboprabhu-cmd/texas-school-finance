-- TEA Excess Local Revenue notification lists (estimates; districts on the list do not necessarily owe recapture)
SELECT year AS school_year_ending, cdn, district_name, tier_one_entitlement, local_fund_assignment,
       tier_one_excess_revenue, tier_one_excess_after_adjustment, district_property_value, wada, county
FROM mart_elr_list ORDER BY year DESC, tier_one_excess_after_adjustment DESC;
