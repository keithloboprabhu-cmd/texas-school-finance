# Manual downloads needed

These sources could not be downloaded automatically from the build environment.
Download each file to the path shown (relative to the repo root), then rerun `make data`.

## Direct files

| Source | Save as | URL |
|---|---|---|
| TEA PEIMS actual financial data | `data/raw/tea_peims/peims_actuals_summarized_2009_2025.xlsx` | https://tea.texas.gov/media/423296 |
| TEA Excess Local Revenue (recapture) district list | `data/raw/tea_recapture/excess_local_revenue_2025_26.pdf` | https://tea.texas.gov/finance-and-grants/state-funding/excess-local-revenue/2025-2026-excess-local-revenue-districts.pdf |
| TEA school district adopted M&O and I&S tax rates, 2006-2025 | `data/raw/tea_tax_rates/school_district_adopted_tax_rates.xlsx` | https://tea.texas.gov/about-tea/state-funding/additional-finance-resources/school-district-adopted-tax-rates-1.xlsx |
| NCES EDGE School District Composites SY 2024-25 (TL 2025) | `data/raw/nces_boundaries/EDGE_SCHOOLDISTRICT_TL25_SY2425.zip` | https://nces.ed.gov/programs/edge/data/EDGE_SCHOOLDISTRICT_TL25_SY2425.zip |
| NCES EDGE public school locations 2024-25 | `data/raw/nces_school_points/EDGE_GEOCODE_PUBLICSCH_2425.zip` | https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_2425.zip |
| CPI-U, all items (CPIAUCSL) | `data/raw/fred_cpi/CPIAUCSL.csv` | https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL |

## Files to pick from a landing page

- **TEA Summary of Finances (SOF)**: https://tea.texas.gov/finance-and-grants/state-funding/foundation-school-program/summary-of-finances. Save into `data/raw/tea_sof/`.
- **Comptroller School District Property Value Study (final findings)**: https://comptroller.texas.gov/taxes/property-tax/pvs/2025f/. Save into `data/raw/comptroller_pvs/`.
- **TEA Texas Academic Performance Reports (district level)**: https://rptsvr1.tea.texas.gov/perfreport/tapr/2024/download.html. Save into `data/raw/tea_tapr/`.
- **Census SAIPE school district estimates (API)**: https://www.census.gov/programs-surveys/saipe/data/api.html. Save into `data/raw/census_saipe/`.
- **Census ACS 5-year estimates by school district (API)**: https://www.census.gov/data/developers/data-sets/acs-5year.html. Save into `data/raw/census_acs/`.
- **NCES Common Core of Data LEA directory (CDN <-> LEAID crosswalk)**: https://nces.ed.gov/ccd/files.asp. Save into `data/raw/nces_ccd_lea/`.
- **Texas Bond Review Board local bond elections (school districts)**: https://debtsearch.brb.texas.gov/bond_elections_search.aspx. Save into `data/raw/brb_bond_elections/`.
  Portal copies listed a last update of June 2020; check freshness before use.
- **Texas Bond Review Board Data Center ISD debt pages**: https://data.brb.texas.gov/local/isd/60.html. Save into `data/raw/brb_debt/`.
  per-district CSVs at https://data.brb.texas.gov/charts/local/isd/<brb_id>/<chart>.csv; BRB id is not the CDN
