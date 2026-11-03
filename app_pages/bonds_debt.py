"""Bonds & Debt: outstanding debt, the maturity profile, CAB exposure and M&O vs I&S tax rates."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from ui import charts, data, maps
from ui.components import (
    big_money,
    growth_effect_text,
    legend_quantile,
    md_money,
    metric,
    money,
    nice,
    notice,
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
from ui.theme import CLAY, INK_2, SEQUENTIAL_7
from ui.theme import html as html_out

if not require_marts("mart_debt_district", "mart_maturity_wall", "mart_tax_rates_state_year"):
    st.stop()

page_header(
    "03 · Borrowing",
    "Bonds & Debt",
    "What Texas school districts owe, when it comes due, and how much of the tax bill goes to debt.",
)

notice(
    "Bond elections aren't shown yet.",
    "Election results (how much a district asked for, what for, and whether voters approved it) come from the "
    "Texas Bond Review Board's search site, debtsearch.brb.texas.gov. Our build couldn't reach that site. The copy "
    "on the Texas Open Data Portal only links to it and was last updated in 2017. We'll add the Ballot Beeswarm "
    "and pass rates once we have the data. Nothing on this page is estimated to fill the gap.",
)

dd = data.query("debt_districts")
ds = data.query("debt_state_year")
fy = int(dd.fiscal_year.max())
first, last = ds.iloc[0], ds.iloc[-1]
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric(
        f"Voter-approved debt owed, fiscal year {fy}",
        big_money(last.tax_supported_principal),
        f"{int(first.fiscal_year)}: {big_money(first.tax_supported_principal)} (not adjusted for inflation)",
    )
with c2:
    metric("Districts with debt", f"{int(last.n_districts):,}")
with c3:
    metric(
        "Typical debt per student (ADA)",
        money(dd.debt_per_ada.median()),
        "debt divided by average daily attendance, as the Bond Review Board reports it",
    )
with c4:
    metric(
        "Debt in deferred-interest bonds (CABs)",
        pct(last.cab_principal / (last.cab_principal + last.cib_principal), 2),
        f"{int(first.fiscal_year)}: {pct(first.cab_principal / (first.cab_principal + first.cib_principal), 2)}",
    )
st.caption(
    f"Source: Texas Bond Review Board, fiscal year {fy} (September to August). Counts debt repaid from property "
    "taxes (general obligation bonds). Leaves out debt due within a year and special obligations that don't need "
    "the Attorney General's approval."
)

# ---------------------------------------------------------------- skyline
rule()
left, right = st.columns([2.3, 1], gap="large")
with left:
    st.subheader("Debt Skyline", anchor=False)
    sk = dd.dropna(subset=["lat", "debt_per_student"]).copy()
    cap = sk.debt_per_student.quantile(0.99)
    sk["elev"] = sk.debt_per_student.clip(upper=cap) / cap * 220_000
    br = maps.quantile_breaks(sk.is_rate)
    sk["color"] = maps.class_colors(maps.classify(sk.is_rate, br), SEQUENTIAL_7)
    sk = sk.join(
        pd.DataFrame(
            [
                maps.tip(
                    nice(n),
                    f"Owes {money(d)} per student in voter-approved debt",
                    f"Total owed: {big_money(p)}",
                    f"Debt tax rate: {maps.cents_per_100(r)}",
                )
                for n, d, p, r in zip(
                    sk.district_name,
                    sk.debt_per_student,
                    sk.tax_supported_principal,
                    sk.is_rate,
                    strict=True,
                )
            ],
            index=sk.index,
        )
    )
    cols = pdk.Layer(
        "ColumnLayer",
        sk,
        id="skyline",
        get_position=["lon", "lat"],
        get_elevation="elev",
        radius=4500,
        get_fill_color="color",
        pickable=True,
        extruded=True,
        disk_resolution=8,
    )
    outline = maps.overlay_layer(data.geojson("tx_outline"), "outline", (27, 26, 23, 255), 1.2)
    st.pydeck_chart(
        maps.deck(
            [outline, cols],
            pdk.ViewState(latitude=30.0, longitude=-99.2, zoom=5.0, pitch=50, bearing=-10),
            "default",
            height=560,
        )
    )
    reading(
        f"Each column is a district. Taller columns owe more voter-approved debt per student. The tallest 1% are "
        f"cut off at {money(cap)} so the rest stay visible. Color shows the debt tax rate (I&S)."
    )
    view_table(
        dd[
            [
                "cdn",
                "district_name",
                "tax_supported_principal",
                "debt_per_student",
                "debt_per_ada",
                "is_rate",
                "cab_share_principal",
            ]
        ],
        "sky",
    )
    view_sql("debt_districts")
with right:
    legend_quantile("Debt tax rate (I&S), per $100 of value", br, lambda v: f"{v * 100:.1f}¢")
    st.markdown("**Owe the most**")
    st.dataframe(
        dd.head(10)[["district_name", "tax_supported_principal", "debt_per_student"]],
        hide_index=True,
        width="stretch",
        column_config={
            "tax_supported_principal": st.column_config.NumberColumn(
                "debt owed ($)", format="localized"
            ),
            "debt_per_student": st.column_config.NumberColumn(
                "per student ($)", format="localized"
            ),
        },
    )

# ---------------------------------------------------------------- maturity
rule()
st.subheader("When the debt is paid off", anchor=False)
mw = data.query("maturity_wall")
fig = go.Figure()
PURPOSE_LABELS = {"New money": "New borrowing", "Refunding": "Refinancing"}
for grp, col in [("New money", INK_2), ("Refunding", "#B9B2A3")]:
    g = mw[mw.purpose_group == grp]
    fig.add_bar(
        x=g.final_maturity_year,
        y=g.debt_service_outstanding / 1e9,
        name=PURPOSE_LABELS[grp],
        marker_color=col,
    )
peak = mw.groupby("final_maturity_year").debt_service_outstanding.sum()
fig.add_annotation(
    x=peak.idxmax(),
    y=peak.max() / 1e9,
    text=f"largest year: {peak.idxmax()}",
    showarrow=True,
    arrowhead=0,
    ax=0,
    ay=-30,
    font=dict(family="JetBrains Mono", size=12),
)
fig.add_vline(x=fy, line=dict(color=CLAY, width=1, dash="dot"))
fig.update_layout(
    barmode="stack",
    yaxis_title="$ billions still owed (principal and interest)",
    xaxis_title="year the debt is fully paid off",
    legend=dict(orientation="h", y=1.08),
)
owed = mw.groupby("final_maturity_year").debt_service_outstanding.sum().sort_index()
half_year = int(owed.index[(owed.cumsum() / owed.sum()) >= 0.5][0])
html_out(
    f'<p class="ll-caption">Half of the money still owed will be paid off by {half_year}. The rest runs '
    f"as late as {int(owed.index.max())}.</p>"
)
charts.show(fig, height=380, key="wall")
reading(
    f"All remaining debt payments, as of fiscal year {fy}, grouped by the year each bond is fully paid off. "
    "The chart doesn't show how much is due in each year. The Bond Review Board doesn't publish each bond's "
    "payment schedule in bulk."
)
view_table(mw, "wall")
view_sql("maturity_wall")

# ---------------------------------------------------------------- CAB + tax anatomy
rule()
a, b = st.columns(2, gap="large")
with a:
    st.subheader("Capital appreciation bonds", anchor=False)
    html_out(
        f'<p class="ll-reading">{term("cab", "CABs")} put off all interest until the end, so the final bill is '
        f"large compared with the amount borrowed. Their share of all school district debt, by year:</p>"
    )
    fig = go.Figure(
        go.Scatter(
            x=ds.fiscal_year,
            y=ds.cab_principal / (ds.cab_principal + ds.cib_principal),
            mode="lines+markers",
            line=dict(color=CLAY),
        )
    )
    cab0 = ds.cab_principal.iloc[0] / (ds.cab_principal.iloc[0] + ds.cib_principal.iloc[0])
    cab1 = ds.cab_principal.iloc[-1] / (ds.cab_principal.iloc[-1] + ds.cib_principal.iloc[-1])
    html_out(
        f'<p class="ll-caption">Districts use far fewer of these costly bonds than they did: {cab0:.1%} of '
        f"debt in {int(ds.fiscal_year.iloc[0])}, {cab1:.1%} in {int(ds.fiscal_year.iloc[-1])}.</p>"
        if cab1 < cab0
        else f'<p class="ll-caption">CABs make up {cab1:.1%} of school district debt, up from {cab0:.1%} in '
        f"{int(ds.fiscal_year.iloc[0])}.</p>"
    )
    fig.update_yaxes(tickformat=".1%", title="share of debt in CABs")
    charts.show(fig, height=260, key="cab")
    cab = dd[dd.cab_principal > 0].sort_values("cab_share_principal", ascending=False).head(20)
    st.dataframe(
        cab[["district_name", "cab_principal", "cab_share_principal"]],
        hide_index=True,
        width="stretch",
        column_config={
            "cab_principal": st.column_config.NumberColumn("owed in CABs ($)", format="localized"),
            "cab_share_principal": st.column_config.NumberColumn(
                "share of district's debt", format="percent"
            ),
        },
    )
    view_sql("debt_state_year", "debt_districts")
with b:
    st.subheader("Tax Anatomy", anchor=False)
    ta = data.query("tax_anatomy")
    share = ta.is_rate_wavg / (ta.mo_rate_wavg + ta.is_rate_wavg)
    fig = go.Figure()
    fig.add_bar(x=ta.year, y=ta.mo_rate_wavg, name="Operations (M&O)", marker_color=INK_2)
    fig.add_bar(x=ta.year, y=ta.is_rate_wavg, name="Debt (I&S)", marker_color=CLAY)
    fig.update_layout(
        barmode="stack",
        yaxis_title="average rate per $100 of property (weighted by enrollment)",
        legend=dict(orientation="h", y=1.1),
    )
    charts.show(fig, height=300, key="anatomy")
    st.markdown(
        md_money(
            f"The debt part of the average school tax rate grew from **{share.iloc[0]:.0%}** in {sy(int(ta.year.iloc[0]))} "
            f"to **{share.iloc[-1]:.0%}** in {sy(int(ta.year.iloc[-1]))}, as the operations rate fell."
        )
    )
    html_out(
        '<p class="ll-caption">'
        + (
            "More of the school tax bill now goes to paying off debt."
            if share.iloc[-1] > share.iloc[0]
            else "Less of the school tax bill now goes to paying off debt."
        )
        + "</p>"
    )
    reading(
        "The operations rate (M&O) pays day-to-day costs. The debt rate (I&S) repays bonds. "
        "These are the rates districts adopted, as reported by TEA."
    )
    view_table(ta, "anatomy")
    view_sql("tax_anatomy")

with st.expander("Tax rates in the 10 largest districts"):
    tl = data.query("tax_anatomy_largest")
    names = tl.district_name.unique()
    cols = st.columns(5)
    for i, n in enumerate(names):
        g = tl[tl.district_name == n]
        f = go.Figure()
        f.add_bar(x=g.year, y=g.mo_rate, marker_color=INK_2, name="M&O")
        f.add_bar(x=g.year, y=g.is_rate, marker_color=CLAY, name="I&S")
        f.update_layout(
            barmode="stack",
            showlegend=False,
            title=dict(text=nice(n), font=dict(size=14)),
            margin=dict(t=30, l=4, r=4, b=4),
            yaxis=dict(range=[0, 2]),
        )
        with cols[i % 5]:
            charts.show(f, height=180, key=f"ta_{i}")
    view_sql("tax_anatomy_largest")

# ---------------------------------------------------------------- growth vs debt
rule()
st.subheader("Do growing districts carry more debt?", anchor=False)
dg = data.query("debt_growth")
dg = dg[~dg.enrollment_caution & (dg.debt_per_student > 0)]
slope, (lo, hi), r2, n = wls_hc1(dg.growth_5y, np.log(dg.debt_per_student), dg.enroll_now)
fig = go.Figure(
    go.Scatter(
        x=dg.growth_5y,
        y=dg.debt_per_student,
        mode="markers",
        marker=dict(size=np.clip(np.sqrt(dg.enroll_now) / 6, 3, 30), color=INK_2, opacity=0.55),
        customdata=dg[["district_name"]],
        hovertemplate="<b>%{customdata[0]}</b><br>growth %{x:.0%}<br>debt/student $%{y:,.0f}<extra></extra>",
    )
)
xs = np.linspace(dg.growth_5y.min(), dg.growth_5y.max(), 50)
a0 = np.average(np.log(dg.debt_per_student) - slope * dg.growth_5y, weights=dg.enroll_now)
fig.add_scatter(
    x=xs, y=np.exp(a0 + slope * xs), mode="lines", line=dict(color=CLAY), hoverinfo="skip"
)
fig.update_xaxes(tickformat=".0%", title="5-year enrollment change")
fig.update_yaxes(type="log", title=f"voter-approved debt per student, fiscal year {fy} (log scale)")
fig.update_layout(showlegend=False)
charts.show(fig, height=420, key="dg")
lead, body = growth_effect_text(
    slope,
    lo,
    hi,
    "Faster-growing districts tend to carry more debt.",
    "Faster-growing districts tend to carry less debt.",
    "owes about **{pct} more** debt per student",
    "owes about **{pct} less** debt per student",
    n,
)
html_out(f'<p class="ll-caption">{lead}</p>')
st.markdown(body)
view_table(dg, "dg")
view_sql("debt_growth")
