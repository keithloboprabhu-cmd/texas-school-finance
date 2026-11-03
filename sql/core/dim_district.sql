-- One row per Texas district (TEA CDN) with every identifier and directory attribute.
-- Universe flags:
--   is_isd       : AskTED district type INDEPENDENT or COMMON (ISDs and common school districts)
--   in_analysis  : is_isd AND has a boundary polygon (charters and non-geographic districts excluded)
--   is_closed_isd: a non-charter district that reported PEIMS actuals in earlier years but no longer
--                  appears in TEA's directory (consolidated or closed); kept in historical marts for
--                  the years it reported (valid_from..valid_to), excluded from maps and profiles
CREATE OR REPLACE TABLE dim_district AS
WITH ask AS (
  SELECT DISTINCT "District Number" AS cdn, "District Name" AS askted_name,
         "District Type" AS district_type, "NCES District ID" AS askted_leaid,
         "County Name" AS county, "County Number" AS county_number,
         "ESC Region Geographic" AS esc_region,
         "District City" AS district_city
  FROM stg_askted
), names AS (  -- most recent PEIMS name for every CDN ever reported, with first/last year
  SELECT cdn, arg_max(district_name, year) AS peims_name, min(year) AS valid_from, max(year) AS valid_to
  FROM stg_peims_summarized GROUP BY cdn
), ids AS (
  SELECT cdn FROM ask UNION SELECT cdn FROM names UNION SELECT cdn FROM stg_ccd_lea
)
SELECT
  ids.cdn,
  coalesce(ccd.leaid, ask.askted_leaid)                         AS leaid,
  coalesce(ccd.leaid, ask.askted_leaid)                         AS geoid,
  coalesce(ask.askted_name, names.peims_name, ccd.ccd_name)     AS district_name,
  ask.district_type,
  coalesce(ask.district_type IN ('INDEPENDENT', 'COMMON'), FALSE)   AS is_isd,
  coalesce(ask.district_type = 'CHARTER' OR ccd.charter_lea = 'LEA for federal programs', FALSE) AS is_charter,
  b.geoid IS NOT NULL                                           AS has_boundary,
  coalesce(ask.district_type IN ('INDEPENDENT', 'COMMON'), FALSE) AND b.geoid IS NOT NULL AS in_analysis,
  ask.county, ask.county_number, ask.esc_region, ask.district_city,
  edge.county_fips, edge.cbsa, edge.cbsa_name, edge.cbsa_type,
  edge.cbsa_type = '1'                                          AS is_metro,
  edge.locale_code, loc.locale, loc.locale_detail,
  edge.hq_lat, edge.hq_lon,
  b.int_lat, b.int_lon, b.aland,
  names.valid_from, names.valid_to,
  ccd.leaid IS NOT NULL AND ask.askted_leaid IS NOT NULL AND ccd.leaid <> ask.askted_leaid AS leaid_conflict,
  ask.cdn IS NULL AND ids.cdn IN (SELECT DISTINCT cdn FROM stg_peims_actuals)
    AND names.valid_to < (SELECT max(year) FROM stg_peims_summarized)                AS is_closed_isd
FROM ids
LEFT JOIN ask USING (cdn)
LEFT JOIN names USING (cdn)
LEFT JOIN stg_ccd_lea ccd USING (cdn)
LEFT JOIN stg_edge_lea edge ON edge.leaid = coalesce(ccd.leaid, ask.askted_leaid)
LEFT JOIN ref_locale loc ON loc.locale_code = edge.locale_code
LEFT JOIN (SELECT * FROM stg_boundaries WHERE sd_type <> 'secondary') b
       ON b.geoid = coalesce(ccd.leaid, ask.askted_leaid);

-- Spec-named crosswalk view
CREATE OR REPLACE VIEW dim_district_xwalk AS
SELECT cdn, leaid, geoid, district_name AS name, county, esc_region, locale, valid_from, valid_to
FROM dim_district;
