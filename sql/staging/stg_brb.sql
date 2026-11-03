-- Texas Bond Review Board: ISD debt outstanding by issuance and state fiscal year (Sept-Aug).
-- pledgetype: GO = tax-supported, Rev = revenue-supported, LP = lease-purchase (as published).
CREATE OR REPLACE VIEW stg_brb_issuance AS
SELECT cdn, governmentid AS brb_id, governmentname AS brb_name, govid, county AS brb_county,
       issuancename, issuepurpose, pledgetype, closingdate, maturitydate, lastprincipalpayment,
       fiscalyear::INTEGER AS fiscal_year, ada, adawealth AS wealth_per_ada, studentheadcount,
       taxratemo, taxrateis, totalprincipaloutstanding AS principal_outstanding,
       totalinterestoutstanding AS interest_outstanding, totaldebtserviceoutstanding AS debt_service_outstanding
FROM read_parquet(getvariable('processed') || '/brb_issuance.parquet');

-- BRB Data Center: CAB vs CIB principal and interest outstanding by district and fiscal year.
CREATE OR REPLACE VIEW stg_brb_cab_cib AS
SELECT cdn, governmentid AS brb_id, fiscalyear::INTEGER AS fiscal_year,
       cibprincipaloutstanding AS cib_principal, cibinterestoutstanding AS cib_interest,
       cabprincipaloutstanding AS cab_principal, cabinterestoutstanding AS cab_interest
FROM read_parquet(getvariable('processed') || '/brb_cab_cib.parquet');
