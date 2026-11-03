-- At least 98% of ISDs/common districts match TEA finance, Census (SAIPE and ACS) and boundaries.
WITH isd AS (SELECT * FROM dim_district WHERE is_isd AND valid_to = (SELECT max(year) FROM stg_peims_summarized))
SELECT count(*) AS n_isd,
       count(*) FILTER (WHERE in_analysis) AS n_boundary,
       count(*) FILTER (WHERE geoid IN (SELECT geoid FROM stg_saipe)) AS n_saipe,
       count(*) FILTER (WHERE geoid IN (SELECT geoid FROM stg_acs)) AS n_acs
FROM isd
HAVING least(n_boundary, n_saipe, n_acs) < 0.98 * n_isd;
