"""Methodology & Data: sources, definitions, exclusions, caveats and data as-of dates."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import data
from ui.components import md_money, page_header, rule, sy
from ui.theme import html as html_out

QA = data.ROOT / "data" / "qa"
latest = int(data.query("meta_years").year.max())

page_header(
    "Methodology & Data",
    "Sources, definitions and caveats",
    "Every number on this site comes from the code in this project's repository (python -m pipeline.build). "
    "This page lists where the data comes from, how we checked it, and what we don't know.",
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
                "Status (date checked)": s.get("status", ""),
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
st.subheader("What's counted and how districts are matched", anchor=False)
html_out(
    '<p class="ll-caption">In short: every Texas school district with a map boundary, one school year at a time. '
    "Charter schools are shown separately.</p>"
)
st.markdown(
    md_money(f"""
- **Unit:** one Texas school district in one school year. Years are labeled by the school year they end, so 2025
  means 2024-25. TEA's PEIMS spending files use the same convention (TEA calls the 2024-25 file "2024-2025
  Financial Actual Data").
- **Which districts:** independent and common school districts that have a map boundary ({sy(latest)}: 1,017).
  Twelve districts that merged or closed since 2008-09 stay in the statewide history for the years they reported.
  **Open-enrollment charter schools** have no boundaries and collect no local property tax. They're left off the maps
  and out of the wealth comparisons, and shown separately on Equity Over Time.
- **Districts left out of the statistics:** 9 districts enroll many students who don't live there, often on
  TEA-flagged virtual campuses. We leave them out of the model, the similar-district matches and the equity measures.
  The rule: at least 25% of October 2025 campus enrollment on virtual campuses, or PEIMS enrollment that differs from
  the campus total in TEA's AskTED directory by more than 50% and more than 500 students.
- **District IDs:** TEA's 6-digit County-District Number (CDN) is always stored as text with leading zeros. The federal
  ID (NCES LEAID, the same as the Census GEOID) is 48 plus 5 digits. We match the two using the NCES CCD district
  directory, where ST_LEAID is "TX-" plus the CDN. The match agrees with TEA's AskTED directory for every district.
  The Bond Review Board's `govid` is the CDN written the Comptroller's way (037-901-02).
""")
)

rule()
st.subheader("Definitions", anchor=False)
html_out(
    '<p class="ll-caption">Each definition starts with what the measure means. The detail after it is for '
    "readers who want to check our work against TEA's own reports.</p>"
)
date_match = data.query("campus_date_match").share_within_one_year.iloc[0]
st.markdown(
    md_money(f"""
**Spending per student (the main measure).** What a district spends in a year to run its schools, per student.
It leaves out debt payments, construction and money sent to the state. In detail, it's day-to-day spending from all funds: PEIMS objects 6100-6400 (payroll,
contracted services, supplies and other operating costs) in operating functions 11-61, plus 92 and 95 as TEA reports
them. Capital projects funds (6xx) are left out. This matches TEA's own "total operating expenditures" for at least 99%
of districts every year, and statewide to 0.000%. We then also remove money a district spends as the fiscal agent for a
**shared services arrangement** (funds 291-379 and 431-459), because that money is spent on behalf of other districts.
The total is divided by fall enrollment and adjusted for inflation.

**Left out of spending, with the TEA accounting codes** (FASRG Update 20):
- Function 71 (debt service) and object 6500 (debt payments)
- Function 81 (buying land and building facilities) and object 6600 (capital purchases)
- Function 91 (purchase of WADA to reduce excess local revenue), which is **recapture**. Counting it would make
  property-wealthy districts look like bigger spenders than they are.
- Functions 93 (payments to shared services fiscal agents), 97 (payments to tax increment funds) and 99 (other
  payments to other governments)
- Function 92 isn't defined in FASRG Update 20, so it is **unverified**. TEA groups it with general administration,
  and we do the same.

**Property wealth per student.** How much taxable property sits behind each student. In detail, it's the
Comptroller's certified value "used for school funding" (from TEA's PTAD Tax
Final files), divided by fall enrollment. We pair school year Y with tax year Y−1, the values the district taxes during
that school year. TEA's own timing has changed over the years: before 2019-20, school funding used the prior year's
values. TEA hasn't posted tax year 2009, so wealth measures start in 2010-11. TEA's tax year 2022 file lists 966
districts. We fill in the rest from the Comptroller's Property Value Study (ASGN T2), which matches TEA's value for
98-100% of districts in the years both exist.

**Inflation adjustment.** We use the Consumer Price Index (CPI-U, FRED series CPIAUCSL), averaged from July to June for
each school year, and show dollars as of the latest school year.

**Household income and poverty.** Median household income comes from the Census ACS 2020-2024 5-year estimates, which cap
it at $250,000. Child poverty is the Census SAIPE 2024 estimate for children 5-17. The shares of students who are from
low-income families (TEA's "economically disadvantaged"), English learners or in special education come from TEA's TAPR
reports for 2023-24.

**Per student.** We divide by fall enrollment everywhere. TEA's attendance-based counts (ADA and WADA) aren't available
for all districts in one file: the Summary of Finances only shows one district at a time. We don't adjust for regional
price differences (the NCES ACS-CWIFT index).

**Small districts.** Fewer than 500 students. We flag them and never drop them. Wealth & Spending lets you hide them.

**Statistics.** We fit simple trend lines and give bigger districts more weight, so a district of 50,000 students
counts for more than one of 50. Statewide measures are weighted by enrollment. "How much spending rises with wealth" (the wealth
elasticity) is the slope of a line fitted to log spending and log wealth, weighted by enrollment, with robust (HC1)
errors. The fuller model also accounts for log enrollment, the shares of low-income students, English learners and
special education students, setting (city, suburb, town or rural) and log students per square mile. We rank districts by
how far they land from that model's prediction, and check the ranking with a Huber robust regression. The McLoone index
divides what students below the median actually get by what they'd get if they were all at the median.

**Debt.** Money districts borrowed with voters' approval and still owe. The data comes from the Texas Bond Review Board, by state fiscal year (September to August). We count debt repaid from
property taxes (general obligation bonds). Debt per ADA follows the Bond Review Board's own measure. The "paid off" chart
groups remaining debt payments by each bond's final year. It isn't a year-by-year payment schedule, because the Bond
Review Board doesn't publish those in bulk.

**New campuses.** Schools that opened in 2016-17 or later. In detail, a school whose federal (NCES) ID first appears after 2015-16, using NCES school locations from 2015-16
to 2024-25. A new ID can also mean an existing school was reorganized. For {date_match:.0%} of new district campuses that TEA's
AskTED directory dates, TEA's date is within a year of the federal listing.

**Construction cost.** Texas has no statewide data on cost per square foot, so we don't show one. Building spending per
student added and per new campus are labeled as **proxies**.
""")
)

rule()
st.subheader("Quality checks", anchor=False)
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("**Do our totals match TEA's?**")
    st.markdown((QA / "reconciliation.md").read_text().split("\n", 2)[2])
    un = pd.read_csv(QA / "unmatched.csv", dtype=str)
    st.markdown(
        f"**District matching:** 1,017 of the 1,019 districts that reported spending in {sy(latest)} match a map "
        f"boundary and Census data (99.8%). {len(un)} districts in TEA's directory have no boundary:"
    )
    st.dataframe(un[["cdn", "district_name", "reason"]], hide_index=True, width="stretch")
with c2:
    st.markdown("**Spot checks on five districts**")
    st.markdown((QA / "spot_checks.md").read_text().split("\n", 2)[2])
    st.markdown("**Color-blindness check**")
    st.markdown((QA / "palette_check.md").read_text().split("\n", 2)[2])

rule()
st.subheader("What we don't know", anchor=False)
st.markdown(
    md_money("""
- **Bond elections are missing.** Our build couldn't reach the Bond Review Board's election search
  (debtsearch.brb.texas.gov), and the open-data copy is only a link, last updated in 2017. So the Ballot Beeswarm, pass
  rates and bond dollars per new seat aren't shown.
- Per-student figures for very small districts swing a lot. One unusual accounting entry can dominate a year. For example,
  one district reported $130,791 per student in 2017-18. We remove values outside $5,000-$60,000, one-year
  spikes, and years with a one-year jump in enrollment, and list every one in `data/qa/anomalies.csv`.
- Student shares (TAPR 2023-24) are one year older than the latest spending data. Census income is a 5-year average.
- Shared services arrangements: services a district buys through one of these arrangements don't count as spending for
  that district (function 93 is left out) or for the fiscal agent (its shared services funds are removed).
- TEA has posted recapture for 2025-26 (near-final) and 2026-27 (preliminary). We don't use them until they're final.
- Everything here shows patterns, not causes. The law markers on Equity Over Time only mark timing.
""")
)

rule()
st.subheader("Glossary", anchor=False)
for entry in data.config("glossary").values():
    st.markdown(md_money(f"**{entry['label']}**: {entry['definition']}"))
