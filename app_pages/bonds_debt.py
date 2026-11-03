"""Bonds & Debt: outstanding debt, the maturity profile, CAB exposure and M&O vs I&S tax rates."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from ui import charts, data, maps
from ui.components import (
    big_money,
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

if not require_marts("mart_debt_district", "mart_maturity_wall", "mart_tax_rates_state_year"):
    st.stop()

page_header(
    "03 · Borrowing",
    "Bonds & Debt",
    "What Texas school districts owe, when it comes due, and how much of the tax bill goes to debt.",
)

notice(
    "Bond elections are not shown yet.",
    "Election results (amount requested, purpose, carried or defeated) come from the Texas Bond Review Board's "
    "search site, debtsearch.brb.texas.gov, which this build could not reach. The Texas Open Data Portal copy is "
    "only a link to that site and was last updated in 2017. The Ballot Beeswarm and pass-rate analysis will be "
    "added once the data is available; nothing here is estimated in their place.",
)

dd = data.query("debt_districts")
ds = data.query("debt_state_year")
fy = int(dd.fiscal_year.max())
first, last = ds.iloc[0], ds.iloc[-1]
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric(
        f"Tax-supported principal, FY{fy}",
        big_money(last.tax_supported_principal),
        f"FY{int(first.fiscal_year)}: {big_money(first.tax_supported_principal)} (nominal)",
    )
with c2:
    metric("Districts with debt", f"{int(last.n_districts):,}")
with c3:
    metric(
        "Median debt per ADA",
        money(dd.debt_per_ada.median()),
        "tax-supported principal / ADA (BRB measure)",
    )
with c4:
    metric(
        "CAB share of principal",
        pct(last.cab_principal / (last.cab_principal + last.cib_principal), 2),
        f"FY{int(first.fiscal_year)}: {pct(first.cab_principal / (first.cab_principal + first.cib_principal), 2)}",
    )
st.caption(
    f"Texas Bond Review Board, state fiscal year (Sept-Aug) {fy}. Tax-supported = general obligation (GO) "
    "pledge. Excludes obligations under one year and special obligations not requiring Attorney General approval."
)

# ---------------------------------------------------------------- skyline
rule()
left, right = st.columns([2.3, 1], gap="large")
with left:
    st.subheader("Debt skyline", anchor=False)
    sk = dd.dropna(subset=["lat", "debt_per_student"]).copy()
    cap = sk.debt_per_student.quantile(0.99)
    sk["elev"] = sk.debt_per_student.clip(upper=cap) / cap * 220_000
    br = maps.quantile_breaks(sk.is_rate)
    sk["color"] = maps.class_colors(maps.classify(sk.is_rate, br), SEQUENTIAL_7)
    sk["tip"] = [
        f"<b>{nice(n)}</b><br/>debt/student {money(d)}<br/>I&S rate {r:.4f}"
        if r == r
        else f"<b>{nice(n)}</b>"
        for n, d, r in zip(sk.district_name, sk.debt_per_student, sk.is_rate, strict=True)
    ]
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
            "{tip}",
            height=560,
        )
    )
    reading(
        f"Each column is a district. Height = tax-supported debt per enrolled student (capped at the 99th "
        f"percentile, {money(cap)}); colour = I&S (debt) tax rate."
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
    legend_quantile("I&S tax rate (per $100)", br, lambda v: f"{v:.3f}")
    st.markdown("**Largest debt loads**")
    st.dataframe(
        dd.head(10)[["district_name", "tax_supported_principal", "debt_per_student"]],
        hide_index=True,
        width="stretch",
        column_config={
            "tax_supported_principal": st.column_config.NumberColumn(
                "principal", format="localized"
            ),
            "debt_per_student": st.column_config.NumberColumn("per student", format="localized"),
        },
    )

# ---------------------------------------------------------------- maturity
rule()
st.subheader("When the debt finishes", anchor=False)
mw = data.query("maturity_wall")
fig = go.Figure()
for grp, col in [("New money", INK_2), ("Refunding", "#B9B2A3")]:
    g = mw[mw.purpose_group == grp]
    fig.add_bar(
        x=g.final_maturity_year, y=g.debt_service_outstanding / 1e9, name=grp, marker_color=col
    )
peak = mw.groupby("final_maturity_year").debt_service_outstanding.sum()
fig.add_annotation(
    x=peak.idxmax(),
    y=peak.max() / 1e9,
    text=f"peak: {peak.idxmax()}",
    showarrow=True,
    arrowhead=0,
    ax=0,
    ay=-30,
    font=dict(family="JetBrains Mono", size=12),
)
fig.add_vline(x=fy, line=dict(color=CLAY, width=1, dash="dot"))
fig.update_layout(
    barmode="stack",
    yaxis_title="$ billions outstanding (principal + interest)",
    xaxis_title="final maturity year",
    legend=dict(orientation="h", y=1.08),
)
charts.show(fig, height=380, key="wall")
reading(
    f"Total remaining debt service (FY{fy}) grouped by each bond's final maturity year. This is not an annual "
    "payment schedule: BRB does not publish per-issuance payment schedules in bulk, so the chart shows when "
    "obligations finish, not when each payment falls."
)
view_table(mw, "wall")
view_sql("maturity_wall")

# ---------------------------------------------------------------- CAB + tax anatomy
rule()
a, b = st.columns(2, gap="large")
with a:
    st.subheader("Capital appreciation bonds", anchor=False)
    st.html(
        f'<p class="ll-reading">{term("cab", "CABs")} defer all interest to maturity, so the final bill is '
        f"large relative to principal. Statewide share of outstanding principal by fiscal year:</p>"
    )
    fig = go.Figure(
        go.Scatter(
            x=ds.fiscal_year,
            y=ds.cab_principal / (ds.cab_principal + ds.cib_principal),
            mode="lines+markers",
            line=dict(color=CLAY),
        )
    )
    fig.update_yaxes(tickformat=".1%", title="CAB share of principal")
    charts.show(fig, height=260, key="cab")
    cab = dd[dd.cab_principal > 0].sort_values("cab_share_principal", ascending=False).head(20)
    st.dataframe(
        cab[["district_name", "cab_principal", "cab_share_principal"]],
        hide_index=True,
        width="stretch",
        column_config={
            "cab_principal": st.column_config.NumberColumn("CAB principal", format="localized"),
            "cab_share_principal": st.column_config.NumberColumn("CAB share", format="percent"),
        },
    )
    view_sql("debt_state_year", "debt_districts")
with b:
    st.subheader("Tax anatomy", anchor=False)
    ta = data.query("tax_anatomy")
    share = ta.is_rate_wavg / (ta.mo_rate_wavg + ta.is_rate_wavg)
    fig = go.Figure()
    fig.add_bar(x=ta.year, y=ta.mo_rate_wavg, name="M&O", marker_color=INK_2)
    fig.add_bar(x=ta.year, y=ta.is_rate_wavg, name="I&S (debt)", marker_color=CLAY)
    fig.update_layout(
        barmode="stack",
        yaxis_title="average rate per $100 (enrollment-weighted)",
        legend=dict(orientation="h", y=1.1),
    )
    charts.show(fig, height=300, key="anatomy")
    st.markdown(
        md_money(
            f"The I&S share of the average school tax rate went from **{share.iloc[0]:.0%}** in {sy(int(ta.year.iloc[0]))} "
            f"to **{share.iloc[-1]:.0%}** in {sy(int(ta.year.iloc[-1]))}, as M&O rates were compressed."
        )
    )
    reading("M&O funds day-to-day operations; I&S repays bonds. Rates are TEA's adopted rates.")
    view_table(ta, "anatomy")
    view_sql("tax_anatomy")

with st.expander("Tax anatomy of the 10 largest districts"):
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
fig.update_yaxes(type="log", title=f"tax-supported debt per student, FY{fy} (log)")
fig.update_layout(showlegend=False)
charts.show(fig, height=420, key="dg")
st.markdown(
    f"Each additional 10 percentage points of 5-year enrollment growth goes with about "
    f"**{(np.exp(slope * 0.1) - 1):+.0%}** more debt per student (95% CI {(np.exp(lo * 0.1) - 1):+.0%} to "
    f"{(np.exp(hi * 0.1) - 1):+.0%}; n = {n:,}, enrollment-weighted). Descriptive, not causal."
)
view_table(dg, "dg")
view_sql("debt_growth")
