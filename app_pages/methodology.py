"""Methodology & Data: sources, definitions, exclusions, caveats and data as-of dates."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import data
from ui.components import md_money, page_header, rule, sy

QA = data.ROOT / "data" / "qa"
latest = int(data.query("meta_years").year.max())

page_header(
    "Methodology & Data",
    "Sources, definitions and caveats",
    "Every number in this atlas comes from the pipeline in this repository (python -m pipeline.build). "
    "This page lists where the data comes from, what was verified, and what is not known.",
)

# ---------------------------------------------------------------- sources
st.subheader("Sources", anchor=False)
src = data.config("sources")
st.dataframe(
    pd.DataFrame(
        [
            {
                "Source": s["name"],
                "Publisher": s["publisher"],
                "Status / as of": s.get("status", ""),
                "Notes": s.get("notes", ""),
                "Link": s["landing"],
            }
            for s in src.values()
        ]
    ),
    hide_index=True,
    width="stretch",
    column_config={
        "Link": st.column_config.LinkColumn(),
        "Notes": st.column_config.TextColumn(width="large"),
    },
)

rule()
st.subheader("Unit, universe and identifiers", anchor=False)
st.markdown(
    md_money(f"""
- **Unit:** Texas school district × school year. A year is labelled by the school year it ends: 2025 = 2024-25.
  TEA's PEIMS actuals use this convention (the 2024-25 single file is TEA's "2024-2025 Financial Actual Data").
- **Universe:** independent and common school districts with a geographic boundary (1,017 in {sy(latest)}).
  Twelve districts that consolidated or closed since 2008-09 are kept in statewide history for the years they reported.
  **Open-enrollment charters** have no boundaries and no local tax base. They are excluded from maps and the wealth analysis
  and reported separately on Equity Over Time.
- **Enrollment caution:** 9 districts (for example those enrolling many students on TEA-flagged virtual campuses) are excluded
  from the model, peers and equity metrics. Rule: at least 25% of October 2025 campus enrollment on virtual campuses, or PEIMS
  enrollment differing from TEA AskTED's campus total by more than 50% and more than 500 students.
- **Identifiers:** TEA's 6-digit County-District Number (CDN) is always a zero-padded string. NCES LEAID = Census
  GEOID = 48 + 5 digits. The crosswalk comes from the NCES CCD LEA directory (ST_LEAID = "TX-" + CDN) and agrees with TEA
  AskTED for every district. The Bond Review Board's `govid` is the CDN in Comptroller format (037-901-02).
""")
)

rule()
st.subheader("Definitions", anchor=False)
st.markdown(
    md_money("""
**Operating spending per student (headline).** All-funds actual expenditures in PEIMS objects 6100-6400 (payroll,
contracted services, supplies, other operating), in operating functions (11-61, plus 92 and 95, as TEA reports them),
excluding capital projects funds (6xx). This reproduces TEA's own "total operating expenditures" for at least 99% of
districts in every year and to 0.000% statewide. The headline then also removes spending in **shared services arrangement
fiscal-agent funds** (291-379, 431-459), which a fiscal agent spends on behalf of member districts. Divided by PEIMS fall
enrollment and expressed in real dollars.

**Excluded from operating spending, with codes** (FASRG Update 20):
- Function 71, Debt Service, and object 6500 (debt service)
- Function 81, Facilities Acquisition and Construction, and object 6600 (capital outlay)
- Function 91, Purchase of WADA to Reduce Excess Local Revenue (**recapture**). Counting it would inflate spending in
  property-wealthy districts.
- Functions 93 (payments to shared services fiscal agents), 97 (payments to tax increment funds) and 99 (other intergovernmental)
- Function 92 is not defined in FASRG Update 20 (**unverified**); TEA groups it with general administration, and so does this project.

**Property wealth per student.** The Comptroller-certified value "used for school funding" (TEA's PTAD Tax Final files),
divided by fall enrollment. School year Y is paired with tax year Y−1, the value the district taxes during that school year.
TEA's own funding lag differs by era: before 2019-20, prior-year values were used. Tax year 2009 is not posted, so
wealth metrics start in 2010-11. TEA's tax year 2022 file lists 966 districts; the rest come from the Comptroller PVS (ASGN T2),
which equals TEA's value for 98-100% of districts in overlapping years.

**Real dollars.** CPI-U (FRED CPIAUCSL) averaged July-June for each school year, in dollars of the latest school year.

**Household income and poverty.** ACS 2020-2024 5-year median household income (top-coded at $250,000) and Census SAIPE
2024 poverty among children 5-17. Economically disadvantaged, English learner and special education shares: TEA TAPR 2023-24.

**Denominators.** Fall enrollment throughout. ADA and WADA are not available in bulk: TEA's Summary of Finances is a
one-district-at-a-time report application. Cost adjustment (NCES ACS-CWIFT) is not applied.

**Small districts.** Under 500 students. Flagged, never dropped, with an option to hide them on Wealth & Spending.

**Statistics.** Equity metrics are enrollment-weighted. Wealth elasticity = slope of log spending on log wealth (WLS,
enrollment weights, HC1 robust errors). The controlled model adds log enrollment, economically disadvantaged, English learner
and special education shares, locale and log students per square mile. Outliers are ranked by standardized residual, with
a Huber robust regression as a sensitivity check. McLoone = spending on students below the median divided by what they
would get at the median.

**Debt.** Texas Bond Review Board, state fiscal year (Sept-Aug). Tax-supported = GO pledge. Debt per ADA follows BRB's
measure. The "maturity" chart groups remaining debt service by each issue's final maturity year; it is not an annual
payment schedule, which BRB does not publish in bulk.

**New campuses.** An NCES school ID first appearing after the 2015-16 baseline (EDGE geocodes 2015-16 to 2024-25). A
new ID can mean a reorganised campus. For 76% of new ISD campuses with an AskTED status date, that date is within a year.

**Construction cost.** Texas has no statewide cost-per-square-foot dataset, so none is shown. Capital spending per student
added and per new campus are labelled **proxies**.
""")
)

rule()
st.subheader("Quality checks", anchor=False)
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("**Reconciliation with TEA published totals**")
    st.markdown((QA / "reconciliation.md").read_text().split("\n", 2)[2])
    un = pd.read_csv(QA / "unmatched.csv", dtype=str)
    st.markdown(
        f"**Crosswalk:** 1,017 of 1,019 ISDs reporting PEIMS in {sy(latest)} match boundaries, SAIPE and ACS "
        f"(99.8%). {len(un)} directory districts have no boundary:"
    )
    st.dataframe(un[["cdn", "district_name", "reason"]], hide_index=True, width="stretch")
with c2:
    st.markdown("**District spot checks**")
    st.markdown((QA / "spot_checks.md").read_text().split("\n", 2)[2])
    st.markdown("**Colour-vision check**")
    st.markdown((QA / "palette_check.md").read_text().split("\n", 2)[2])

rule()
st.subheader("Known limitations", anchor=False)
st.markdown(
    md_money("""
- **Bond elections are missing.** The BRB election search (debtsearch.brb.texas.gov) was not reachable from the build, and
  the open-data copy is a link last updated in 2017. The Ballot Beeswarm, pass rates and bond dollars per new seat are not shown.
- Per-student figures for very small districts are volatile; one-off accounting entries can dominate a year (for example
  one district reporting $130,791 per student in 2017-18). Out-of-bounds values are logged in `data/qa/spending_bounds_log.csv`,
  never dropped.
- Demographic shares (TAPR 2023-24) lag the latest finance year by one year. ACS income is a 5-year average.
- SSA adjustment: services that members buy through a shared services arrangement are counted for neither the member
  (function 93 is excluded) nor the fiscal agent (SSA funds removed).
- Recapture amounts for 2025-26 (near-final) and 2026-27 (preliminary) are reported by TEA but not used in analysis until final.
- All relationships shown are descriptive, not causal. Law-change markers on Equity Over Time mark timing only.
""")
)

rule()
st.subheader("Glossary", anchor=False)
for entry in data.config("glossary").values():
    st.markdown(md_money(f"**{entry['label']}**: {entry['definition']}"))
