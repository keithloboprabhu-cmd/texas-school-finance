"""Growth & Construction: enrollment growth, new campuses and capital spending."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from ui import charts, data, maps
from ui.components import (
    legend_diverging,
    metric,
    money,
    nice,
    page_header,
    pct,
    reading,
    require_marts,
    rule,
    sy,
    term,
    view_sql,
    view_table,
)
from ui.stats import wls_hc1
from ui.theme import CLAY, INK_2
from ui.theme import html as html_out

if not require_marts("mart_growth_capital", "mart_campuses"):
    st.stop()

latest = data.query("meta_years").year.max()
page_header(
    "04 · Building", "Growth & Construction", "Where Texas is growing, and where it is building."
)

g = data.query("growth")
camp = data.query("new_campuses")
show_flagged = st.toggle(
    "Include districts flagged for large virtual or non-resident enrollment",
    value=False,
    help="Nine districts whose reported enrollment includes many students who do not live there.",
)
gv = g if show_flagged else g[~g.enrollment_caution]

c1, c2, c3, c4 = st.columns(4)
added = (gv.enroll_now - gv.enroll_5y_ago).clip(lower=0)
with c1:
    metric(
        "Campuses opened since 2016-17",
        f"{len(camp):,}",
        f"{int((~camp.is_charter).sum()):,} in ISDs, {int(camp.is_charter.sum()):,} charter",
    )
with c2:
    metric(
        "Districts growing >10% in 5 years",
        f"{int((gv.growth_5y > 0.10).sum()):,}",
        f"of {len(gv):,}",
    )
with c3:
    metric("Districts shrinking >10%", f"{int((gv.growth_5y < -0.10).sum()):,}")
top10 = (
    gv.dropna(subset=["enroll_10y_ago"])
    .assign(d=lambda x: x.enroll_now - x.enroll_10y_ago)
    .nlargest(10, "d")
)
isd_new = camp[~camp.is_charter]
share_top = isd_new.district_name.isin(top10.district_name).mean()
with c4:
    metric(
        "ISD new campuses in the 10 fastest-adding districts",
        pct(share_top, 0),
        "fastest-adding = most students added over 10 years",
    )

# ---------------------------------------------------------------- where Texas is building
rule()
st.subheader("Where Texas is building", anchor=False)
yr = st.slider(
    "Campuses opened through",
    2017,
    int(camp.first_year.max()),
    int(camp.first_year.max()),
    format="%d",
    help="School year ending (2017 = 2016-17).",
)
shown = camp[camp.first_year <= yr]
geo = maps.features_with(
    data.geojson("tx_districts_simplified"),
    gv.merge(data.query("atlas_layers", year=int(latest))[["cdn", "geoid"]], on="cdn"),
    ["cdn", "district_name", "growth_10y"],
)
vals = [f["properties"]["growth_10y"] for f in geo["features"]]

cols = maps.diverging_colors(pd.Series(vals, dtype=float), 0.0)
for f, c in zip(geo["features"], cols, strict=True):
    f["properties"]["fill"] = c[:3] + [150]
    g10 = f["properties"]["growth_10y"]
    line = (
        "No enrollment history"
        if g10 is None or g10 != g10
        else (f"Enrollment {'grew' if g10 >= 0 else 'shrank'} {abs(g10):.0%} over 10 years")
    )
    f.update(maps.tip(nice(f["properties"]["district_name"]), line))
fill = pdk.Layer(
    "GeoJsonLayer",
    geo,
    id="growth",
    get_fill_color="properties.fill",
    get_line_color=[251, 248, 242, 120],
    line_width_min_pixels=0.3,
    pickable=True,
)
hexes = pdk.Layer(
    "HexagonLayer",
    shown,
    id="hex",
    get_position=["lon", "lat"],
    radius=9000,
    elevation_scale=350,
    extruded=True,
    coverage=0.85,
    color_range=[
        [236, 230, 217],
        [217, 168, 143],
        [192, 112, 90],
        [168, 67, 42],
        [143, 58, 36],
        [110, 40, 24],
    ],
)
left, right = st.columns([2.3, 1], gap="large")
with left:
    st.pydeck_chart(
        maps.deck(
            [fill, hexes],
            pdk.ViewState(latitude=30.9, longitude=-98.2, zoom=5.3, pitch=40, bearing=-8),
            "default",
            height=580,
        )
    )
    reading(
        f"Hexagons: new campuses opened 2016-17 through {sy(yr)}, counted on a 9 km hex grid (taller = more). "
        "District fill: 10-year enrollment change (clay = growing, teal = shrinking)."
    )
    view_table(shown, "camp")
    view_sql("new_campuses", "growth")
with right:
    legend_diverging("10-year enrollment change", "shrinking", "growing")
    st.markdown("**Fastest-adding districts** (students added, 10 years)")
    st.dataframe(
        top10.assign(name=top10.district_name.map(nice))[
            ["name", "enroll_10y_ago", "enroll_now", "new_campuses_since_2016_17"]
        ],
        hide_index=True,
        width="stretch",
        column_config={
            "enroll_10y_ago": "10 yrs ago",
            "enroll_now": "now",
            "new_campuses_since_2016_17": "new campuses",
        },
    )
    st.caption(
        "New campus = an NCES school ID that first appears after 2015-16. A new ID can also mean a "
        "reorganised campus, so this is an upper bound on new buildings. For 76% of new ISD campuses with a "
        "TEA AskTED status date, the date falls within a year of NCES's first listing."
    )

# ---------------------------------------------------------------- capital intensity
rule()
st.subheader("Capital intensity vs. growth", anchor=False)
ci = gv.dropna(subset=["growth_5y", "capital_per_student_5y_avg"])
ci = ci[(ci.enroll_5y_ago >= 500) & (ci.capital_per_student_5y_avg > 0)]
b, (lo, hi), r2, n = wls_hc1(ci.growth_5y, np.log(ci.capital_per_student_5y_avg), ci.enroll_now)
med_g, med_c = ci.growth_5y.median(), ci.capital_per_student_5y_avg.median()
flag = np.select(
    [
        (ci.growth_5y < 0)
        & (ci.capital_per_student_5y_avg > ci.capital_per_student_5y_avg.quantile(0.9)),
        (ci.growth_5y > ci.growth_5y.quantile(0.9)) & (ci.capital_per_student_5y_avg < med_c),
    ],
    ["building without growth", "growing without building"],
    "",
)
ci = ci.assign(flag=flag)
fig = go.Figure()
for lab, colr in [
    ("", INK_2),
    ("building without growth", "#31688E"),
    ("growing without building", CLAY),
]:
    s = ci[ci.flag == lab]
    fig.add_scatter(
        x=s.growth_5y,
        y=s.capital_per_student_5y_avg,
        mode="markers",
        name=lab or "other districts",
        marker=dict(size=np.clip(np.sqrt(s.enroll_now) / 6, 3, 30), color=colr, opacity=0.6),
        customdata=s[["district_name"]],
        hovertemplate="<b>%{customdata[0]}</b><br>5-yr growth %{x:.0%}<br>capital/student $%{y:,.0f}<extra></extra>",
    )
fig.update_xaxes(tickformat=".0%", title="5-year enrollment change")
fig.update_yaxes(
    type="log", title=f"capital spending per student, 5-yr avg ({sy(int(latest))} $, log)"
)
fig.update_layout(legend=dict(orientation="h", y=1.08))
charts.show(fig, height=440, key="ci")
st.markdown(
    f"Ten more percentage points of growth go with about **{np.exp(b * 0.1) - 1:+.0%}** more capital spending "
    f"per student (95% CI {np.exp(lo * 0.1) - 1:+.0%} to {np.exp(hi * 0.1) - 1:+.0%}; n = {n:,} districts with "
    "at least 500 students, enrollment-weighted). Capital = facilities acquisition and construction (function 81) "
    "plus capital outlay objects (6600), all funds."
)
view_table(ci[["cdn", "district_name", "growth_5y", "capital_per_student_5y_avg", "flag"]], "ci")
view_sql("growth")

# ---------------------------------------------------------------- proxies
rule()
st.subheader("Cost per new seat: proxies", anchor=False)
html_out(
    f'<p class="ll-reading">Texas has no statewide dataset of school construction cost per square foot, so none is '
    f"shown. These are {term('proxy', 'proxies')}: real capital spending over five years divided by students added "
    f"(districts adding at least 50) or by campuses opened in the same window. They mix new schools with "
    f"renovation, land and equipment.</p>"
)
px = gv.dropna(subset=["proxy_capital_per_new_student"]).sort_values(
    "proxy_capital_per_new_student"
)
st.dataframe(
    px[
        [
            "district_name",
            "students_added_5y",
            "new_campuses_5y",
            "capital_5y_real",
            "proxy_capital_per_new_student",
            "proxy_capital_per_new_campus",
            "small_district",
        ]
    ],
    hide_index=True,
    width="stretch",
    column_config={
        "capital_5y_real": st.column_config.NumberColumn(
            "capital, 5 yrs (real $)", format="localized"
        ),
        "proxy_capital_per_new_student": st.column_config.NumberColumn(
            "PROXY: $ per student added", format="localized"
        ),
        "proxy_capital_per_new_campus": st.column_config.NumberColumn(
            "PROXY: $ per new campus", format="localized"
        ),
        "small_district": "under 500",
    },
)
view_sql("growth")
_ = money
