-- Property mix by district (Comptroller PVS assigned values by PTAD category), tax years 2022-2025.
CREATE OR REPLACE TABLE mart_property_mix AS
SELECT p.cdn, p.tax_year, d.district_name, d.county, d.esc_region,
  p.value_category_total,
  p.value_minerals / nullif(p.value_category_total, 0)                         AS mineral_share,
  (p.value_commercial_real + p.value_commercial_personal) / nullif(p.value_category_total, 0) AS commercial_share,
  (p.value_industrial_real + p.value_industrial_personal) / nullif(p.value_category_total, 0) AS industrial_share,
  p.value_utilities / nullif(p.value_category_total, 0)                        AS utility_share,
  (p.value_single_family_residential + p.value_multifamily_residential + p.value_mobile_homes)
     / nullif(p.value_category_total, 0)                                        AS residential_share,
  (p.value_qualified_ag_land + p.value_farm_ranch_improvements + p.value_rural_non_ag)
     / nullif(p.value_category_total, 0)                                        AS rural_land_share
FROM stg_property_mix p JOIN dim_district d USING (cdn)
WHERE d.in_analysis;
