"""Equity Over Time: statewide spending equity, 2008-09 to the latest year, in real dollars."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from ui import charts, data
from ui.components import (
    md_money,
    money,
    nice,
    page_header,
    reading,
    require_marts,
    rule,
    sy,
    term,
    view_sql,
    view_table,
)
from ui.theme import CLAY, INK_2, RULE
from ui.theme import html as html_out

if not require_marts("mart_equity_state_year"):
    st.stop()

eq = data.query("equity")
events = data.config("events")["events"]
y0, y1 = int(eq.year.min()), int(eq.year.max())
page_header(
    "05 · Over time",
    "Equity Over Time",
    "How unequal is per-student spending across Texas districts, and how has that changed?",
)

first, last = eq.iloc[0], eq.iloc[-1]
w0 = eq.dropna(subset=["elasticity"]).iloc[0]
st.markdown(
    md_money(
        f"From {sy(y0)} to {sy(y1)}, the enrollment-weighted average real operating spending per student went from "
        f"**{money(first.mean_spend)}** to **{money(last.mean_spend)}** ({sy(y1)} dollars). The "
        f"{term('mcloone', 'McLoone index')} moved from **{first.mcloone:.3f}** to **{last.mcloone:.3f}**, and the "
        f"spending gap between the wealthiest and poorest fifths of students (by property wealth) went from "
        f"**{w0.quintile_gap_ratio - 1:+.1%}** in {sy(int(w0.year))} to **{last.quintile_gap_ratio - 1:+.1%}**."
    ),
    unsafe_allow_html=True,
)
st.caption(
    "Descriptive trends, not causal estimates of any law. Universe: ISDs and common districts (including "
    "those since consolidated, for the years they reported), excluding 9 districts with large virtual or "
    "non-resident enrollment. Property-wealth metrics start in 2010-11 (tax year 2010)."
)

# ---------------------------------------------------------------- small multiples
metrics = [
    ("cv_bounded", "Coefficient of variation", "lower = more equal", ".3f"),
    ("mcloone", "McLoone index", "higher = more equal", ".3f"),
    ("restricted_range_ratio", "Restricted range (95th / 5th pct.)", "lower = more equal", ".2f"),
    ("elasticity", "Wealth elasticity of spending", "0 = spending independent of wealth", ".3f"),
    ("wealth_spend_corr", "Correlation, log wealth vs. log spending", "0 = no relationship", ".2f"),
    ("quintile_gap_ratio", "Top vs. bottom wealth quintile spending", "1 = no gap", ".3f"),
]
fig = make_subplots(
    rows=2,
    cols=3,
    subplot_titles=[f"{t}<br><sup>{s}</sup>" for _, t, s, _ in metrics],
    shared_xaxes=True,
    vertical_spacing=0.18,
    horizontal_spacing=0.07,
)
for i, (col, _t, _s, fmt) in enumerate(metrics):
    r, c = i // 3 + 1, i % 3 + 1
    if col == "elasticity":
        e = eq.dropna(subset=["elasticity"])
        fig.add_scatter(
            x=list(e.year) + list(e.year[::-1]),
            y=list(e.elasticity_hi) + list(e.elasticity_lo[::-1]),
            fill="toself",
            fillcolor="rgba(92,88,80,0.15)",
            line=dict(width=0),
            hoverinfo="skip",
            row=r,
            col=c,
        )
    if col == "cv_bounded":
        fig.add_scatter(
            x=eq.year,
            y=eq.cv,
            mode="lines",
            line=dict(color=RULE, width=1, dash="dot"),
            hovertemplate="raw CV %{y:.3f}<extra></extra>",
            row=r,
            col=c,
        )
    fig.add_scatter(
        x=eq.year,
        y=eq[col],
        mode="lines+markers",
        line=dict(color=INK_2, width=1.6),
        marker=dict(size=4),
        hovertemplate=f"%{{x}}: %{{y:{fmt}}}<extra></extra>",
        row=r,
        col=c,
    )
    for ev in events:
        if ev["school_year"] <= y1:
            fig.add_vline(
                x=ev["school_year"] - 0.5, line=dict(color=CLAY, width=1, dash="dot"), row=r, col=c
            )
fig.update_layout(showlegend=False, margin=dict(t=70))
fig.update_annotations(font=dict(size=13, family="Inter Tight"))
charts.show(fig, height=560, key="sm")
marker_text = "; ".join(
    f'<a href="{e["source"]}">{e["label"]}</a> (enacted {e["date"]}, first affects {sy(e["school_year"])})'
    for e in events
)
html_out(
    f'<p class="ll-reading">Clay dotted line: law changes with a cited primary source: {marker_text}. Changes '
    f"after {sy(y1)} are listed but not plotted. CV: solid = within the $5k-$60k plausibility bounds, dotted = "
    "all district-years (one district reporting $130,791 per student in 2017-18 drives the spike).</p>"
)
view_table(eq, "eq")
view_sql("equity")

# ---------------------------------------------------------------- ridgeline
rule()
st.subheader("The distribution, year by year", anchor=False)
dist = data.query("equity_distribution")
grid = np.linspace(6000, 24000, 220)
fig = go.Figure()
yrs = sorted(dist.year.unique())
for k, yr in enumerate(yrs):
    g = dist[dist.year == yr]
    x, w = g.op_per_student_real.values, g.enrollment.values
    bw = 0.06 * np.average(x, weights=w)
    dens = (w[:, None] * np.exp(-0.5 * ((grid[None, :] - x[:, None]) / bw) ** 2)).sum(0)
    dens = dens / dens.max() * 1.6
    base = len(yrs) - 1 - k
    fig.add_scatter(
        x=grid,
        y=base + dens,
        mode="lines",
        line=dict(color=INK_2, width=1),
        fill="toself" if False else None,
        hoverinfo="skip",
    )
    fig.add_scatter(
        x=np.r_[grid, grid[::-1]],
        y=np.r_[base + dens, np.full_like(grid, base)],
        fill="toself",
        fillcolor="rgba(236,230,217,0.9)",
        line=dict(width=0),
        hoverinfo="skip",
    )
    fig.add_scatter(
        x=grid, y=base + dens, mode="lines", line=dict(color="#1B1A17", width=1), hoverinfo="skip"
    )
    med = eq.loc[eq.year == yr, "median_spend"].iloc[0]
    fig.add_scatter(
        x=[med, med],
        y=[base, base + 1.0],
        mode="lines",
        line=dict(color=CLAY, width=2),
        hovertemplate=f"{sy(int(yr))} median ${med:,.0f}<extra></extra>",
    )
fig.update_yaxes(
    tickvals=list(range(len(yrs))), ticktext=[sy(int(y)) for y in yrs[::-1]], showgrid=False
)
fig.update_xaxes(
    title=f"operating spending per student ({sy(y1)} $)", tickprefix="$", range=[6000, 24000]
)
fig.update_layout(showlegend=False)
charts.show(fig, height=640, key="ridge")
reading(
    "Each ridge is one year's distribution of students by their district's real spending per student "
    "(enrollment-weighted density). Clay tick = median. Districts above $24,000 are off the right edge."
)
view_sql("equity_distribution")

# ---------------------------------------------------------------- rank slope
rule()
st.subheader(f"Who moved: spending rank, {sy(y0)} vs. {sy(y1)}", anchor=False)
rs = data.query("rank_slope")
rs["move"] = rs.rank_first - rs.rank_latest
big = rs[rs.enrollment >= 5000].copy()
up, down = big.nlargest(6, "move"), big.nsmallest(6, "move")
fig = go.Figure()
for r in big.itertuples():
    fig.add_scatter(
        x=[0, 1],
        y=[r.rank_first, r.rank_latest],
        mode="lines",
        line=dict(color=RULE, width=0.7),
        hoverinfo="skip",
    )
for sub, colr in [(up, CLAY), (down, "#31688E")]:
    for r in sub.itertuples():
        fig.add_scatter(
            x=[0, 1],
            y=[r.rank_first, r.rank_latest],
            mode="lines+markers+text",
            line=dict(color=colr, width=2),
            text=["", nice(r.district_name)],
            textposition="middle right",
            textfont=dict(size=12, color=colr),
            hovertemplate=f"{nice(r.district_name)}: %{{y}}<extra></extra>",
        )
fig.update_yaxes(autorange="reversed", title="rank of real spending per student (1 = highest)")
fig.update_xaxes(
    tickvals=[0, 1],
    ticktext=[sy(int(rs.first_year.iloc[0])), sy(int(rs.latest_year.iloc[0]))],
    range=[-0.1, 1.6],
    showgrid=False,
)
fig.update_layout(showlegend=False)
charts.show(fig, height=560, key="slope")
reading(
    "Districts with at least 5,000 students. Clay: biggest climbers in the spending ranking; blue: biggest "
    "fallers; grey: everyone else. Ranks are among all districts statewide."
)
view_table(rs.sort_values("move", ascending=False), "rs")
view_sql("rank_slope")

# ---------------------------------------------------------------- charters
rule()
st.subheader("Open-enrollment charters (reported separately)", anchor=False)
ch = data.query("charters")
st.caption(
    "Charters have no boundaries and no local property tax base, so they are outside the wealth analysis. "
    "TEA operating definition, nominal dollars."
)
st.dataframe(
    ch,
    hide_index=True,
    width="stretch",
    column_config={
        "operating_tea_def": st.column_config.NumberColumn("operating $", format="localized"),
        "op_per_student_nominal": st.column_config.NumberColumn(
            "per student $", format="localized"
        ),
    },
)
view_sql("charters")
