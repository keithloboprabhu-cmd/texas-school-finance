"""Wealth & Spending: how per-student spending tracks property wealth, and the outliers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import charts, data
from ui.components import (
    glossary_help,
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

if not require_marts("mart_district_year", "mart_outliers_latest", "mart_model_latest"):
    st.stop()

years = data.query("meta_years").year.tolist()
latest = years[-1]
page_header(
    "01 · The core question",
    "Wealth & Spending",
    "Does a district's property wealth per student predict how much it spends per student?",
)

c1, c2, c3 = st.columns([1, 1.4, 1.6])
with c1:
    yopts = [y for y in years if y >= 2011][::-1]  # property values start with tax year 2010
    year = st.selectbox("School year", yopts, format_func=sy)
with c2:
    hide_small = st.toggle(
        "Hide districts under 500 students",
        value=False,
        help="Very small districts cost more per student to run, and their figures swing a lot from year to year.",
    )
    color_by = st.segmented_control(
        "Color dots by",
        ["Econ. disadvantaged %", "Locale"],
        default="Econ. disadvantaged %",
        format_func={
            "Econ. disadvantaged %": "Low-income students",
            "Locale": "City, suburb, town or rural",
        }.get,
    )
with c3:
    st.caption(
        "Per student means per student enrolled in the fall. TEA doesn't publish attendance-based counts "
        "(ADA and WADA) for every district in one file, so we don't use them. Costs aren't adjusted for "
        "regional price differences. See Methodology."
    )

df = data.query("wealth_spending", year=year)
flagged = df[df.enrollment_caution]
df = df[~df.enrollment_caution]
if hide_small:
    df = df[~df.small_district]

b, (lo, hi), r2, n = wls_hc1(
    np.log(df.wealth_per_student_real), np.log(df.op_per_student_real), df.enrollment
)

left, right = st.columns([2.3, 1], gap="large")
with right:
    html_out(
        f'<div class="ll-kicker">{term("elasticity", "How much spending rises with wealth")}, {sy(year)}</div>'
    )
    html_out(
        f'<div class="ll-metric"><div class="value">{b:+.3f}</div>'
        f'<div class="label">Likely range {lo:+.3f} to {hi:+.3f} · fit (R²) {r2:.2f} · {n:,} districts</div></div>'
    )
    st.markdown(
        f"A district with **10% more property wealth per student spends about {b * 10:+.2f}% more** per student "
        f"(likely range {lo * 10:+.2f}% to {hi * 10:+.2f}%). Zero would mean wealth makes no difference to spending."
    )
    st.caption(
        f"Method: a line fitted to log spending and log wealth, weighted by enrollment, with robust (HC1) "
        f"standard errors. Leaves out {len(flagged)} districts with many virtual or out-of-district students"
        + (" and districts under 500 students." if hide_small else ".")
    )
    if year == latest:
        coefs = data.query("model_latest")
        cw = coefs[(coefs.model == "controlled") & (coefs.term == "log_wealth")].iloc[0]
        st.markdown(
            f"**Comparing similar districts** (same size, student needs, setting and density): **{cw.coef:+.3f}** "
            f"(likely range {cw.ci_lo:+.3f} to {cw.ci_hi:+.3f})."
        )
        with st.expander("Full model results"):
            st.dataframe(
                coefs[coefs.model.isin(["controlled", "huber"])][
                    ["model", "term", "coef", "ci_lo", "ci_hi", "p_value", "n"]
                ].round(4),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                '"controlled" is the main model: weighted by enrollment, with robust (HC1) errors. "huber" is a '
                "check that gives less weight to extreme districts. Student shares come from TAPR 2023-24. Each "
                "setting is compared with cities."
            )

with left:
    fig = go.Figure()
    if color_by == "Locale":
        palette = {"City": "#31688E", "Suburb": "#35B779", "Town": "#A8432A", "Rural": "#5C5850"}
        for loc, g in df.groupby("locale"):
            fig.add_scatter(
                x=g.wealth_per_student_real,
                y=g.op_per_student_real,
                mode="markers",
                name=loc,
                marker=dict(
                    size=np.clip(np.sqrt(g.enrollment) / 6, 3, 34),
                    color=palette.get(loc, INK_2),
                    opacity=0.65,
                    line=dict(width=0.5, color="#FBF8F2"),
                ),
                customdata=g[["district_name", "enrollment"]],
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,} students<br>wealth $%{x:,.0f}<br>spend $%{y:,.0f}<extra></extra>",
            )
    else:
        fig.add_scatter(
            x=df.wealth_per_student_real,
            y=df.op_per_student_real,
            mode="markers",
            name="districts",
            marker=dict(
                size=np.clip(np.sqrt(df.enrollment) / 6, 3, 34),
                color=df.econ_disadv_pct,
                colorscale="Viridis",
                cmin=0,
                cmax=1,
                opacity=0.7,
                colorbar=dict(title="low-income", tickformat=".0%", thickness=10),
                line=dict(width=0.5, color="#FBF8F2"),
            ),
            customdata=df[["district_name", "enrollment"]],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,} students<br>wealth $%{x:,.0f}<br>spend $%{y:,.0f}<extra></extra>",
        )
    xs = np.linspace(
        np.log(df.wealth_per_student_real.min()), np.log(df.wealth_per_student_real.max()), 50
    )
    a = np.average(
        np.log(df.op_per_student_real) - b * np.log(df.wealth_per_student_real),
        weights=df.enrollment,
    )
    fig.add_scatter(
        x=np.exp(xs),
        y=np.exp(a + b * xs),
        mode="lines",
        line=dict(color=CLAY, width=2),
        name="weighted fit",
        hoverinfo="skip",
    )
    fig.update_xaxes(
        type="log", title=f"Taxable property per student ({sy(latest)} dollars, log scale)"
    )
    fig.update_yaxes(type="log", title=f"Spending per student ({sy(latest)} dollars, log scale)")
    fig.update_layout(legend=dict(orientation="h", y=1.05))
    charts.show(fig, height=560, key="ws_scatter")
    reading(
        "Each dot is a district. Bigger dots have more students. If the clay line is flat, spending doesn't rise with wealth."
    )
    view_table(
        df[
            [
                "cdn",
                "district_name",
                "enrollment",
                "wealth_per_student_real",
                "op_per_student_real",
                "econ_disadv_pct",
                "locale",
            ]
        ],
        "ws",
    )
    view_sql("wealth_spending", "model_latest")

# ---------------------------------------------------------------- outliers
rule()
st.subheader(f"Districts that spend far more or less than expected, {sy(latest)}", anchor=False)
html_out(
    f'<p class="ll-reading">We predict each district\'s spending from its wealth, size, student needs, setting and '
    f'density, then rank districts by how far they land from that prediction. The "why it might be" notes use '
    f"only this site's data. ⚑ means the ranking changes under {term('huber', 'Huber robust regression')}, "
    "which gives less weight to extreme districts.</p>"
)
ol = data.query("outliers_latest")


def outlier_table(sub: pd.DataFrame, key: str):
    t = sub.assign(
        district=sub.district_name.map(nice) + np.where(sub.method_sensitive, " ⚑", ""),
        actual=sub.op_per_student_real,
        predicted=sub.predicted_real,
        recapture=np.where(sub.recapture_paid > 0, "yes", ""),
        small=np.where(sub.small_district, "<500", ""),
        profile="/district?district=" + sub.cdn,
    )[
        [
            "district",
            "county",
            "enrollment",
            "actual",
            "predicted",
            "std_residual",
            "small",
            "recapture",
            "hint",
            "profile",
        ]
    ]
    st.dataframe(
        t,
        hide_index=True,
        width="stretch",
        key=key,
        column_config={
            "actual": st.column_config.NumberColumn("spends per student ($)", format="localized"),
            "predicted": st.column_config.NumberColumn("predicted ($)", format="localized"),
            "small": st.column_config.TextColumn("small"),
            "recapture": st.column_config.TextColumn("pays recapture"),
            "std_residual": st.column_config.NumberColumn("vs. prediction (score)", format="%+.1f"),
            "hint": st.column_config.TextColumn("why it might be", width="large"),
            "profile": st.column_config.LinkColumn("profile", display_text="open →"),
        },
    )


o1, o2 = st.columns(2, gap="large")
with o1:
    st.markdown("**Spends much more than predicted** (top 15)")
    outlier_table(ol[ol.direction == "over"].sort_values("std_residual", ascending=False), "over")
with o2:
    st.markdown("**Spends much less than predicted** (bottom 15)")
    outlier_table(ol[ol.direction == "under"].sort_values("std_residual"), "under")
view_sql("outliers_latest")

# ---------------------------------------------------------------- two wealths
rule()
st.subheader("Two kinds of wealth", anchor=False)
html_out(
    f'<p class="ll-reading">{term("property_wealth", "Property wealth")} is what a district can tax. Household '
    "income is what the people who live there earn. The two don't always match. A district with oil wells or a "
    "refinery can be rich in property while its families earn little, and the reverse happens too.</p>"
)
tw = data.query("wealth_spending", year=latest)
tw = tw[~tw.enrollment_caution].dropna(subset=["median_household_income"])
mx, my = tw.wealth_per_student_real.median(), tw.median_household_income.median()
quad = np.select(
    [
        (tw.wealth_per_student_real >= mx) & (tw.median_household_income < my),
        (tw.wealth_per_student_real < mx) & (tw.median_household_income >= my),
        (tw.wealth_per_student_real >= mx),
    ],
    ["property-rich, income-poor", "income-rich, property-poor", "rich on both"],
    "poor on both",
)
tw = tw.assign(quadrant=quad)
fig = go.Figure()
qcol = {
    "property-rich, income-poor": CLAY,
    "income-rich, property-poor": "#31688E",
    "rich on both": "#574249",
    "poor on both": "#B9B2A3",
}
for q, g in tw.groupby("quadrant"):
    fig.add_scatter(
        x=g.wealth_per_student_real,
        y=g.median_household_income,
        mode="markers",
        name=f"{q} ({len(g)})",
        marker=dict(size=6, color=qcol[q], opacity=0.75),
        customdata=g[["district_name", "recapture_paid"]],
        hovertemplate="<b>%{customdata[0]}</b><br>wealth $%{x:,.0f}<br>income $%{y:,.0f}<br>recapture $%{customdata[1]:,.0f}<extra></extra>",
    )
fig.add_vline(x=mx, line=dict(color=INK_2, width=1, dash="dot"))
fig.add_hline(y=my, line=dict(color=INK_2, width=1, dash="dot"))
fig.update_xaxes(type="log", title="Taxable property per student (log scale)")
fig.update_yaxes(title="Typical household income (Census, 2020-2024)", tickprefix="$")
fig.update_layout(legend=dict(orientation="h", y=1.08))
charts.show(fig, height=460, key="two_wealths")
pr = tw[tw.quadrant == "property-rich, income-poor"]
st.markdown(
    f"**{len(pr)} districts** are above the Texas median in property wealth but below it in household "
    f"income. {int((pr.recapture_paid > 0).sum())} of them sent recapture to the state in {sy(latest)}."
)
reading(
    "The dotted lines mark the middle district on each measure. The Census caps reported income at $250,000."
)
view_table(
    tw[
        [
            "cdn",
            "district_name",
            "wealth_per_student_real",
            "median_household_income",
            "quadrant",
            "recapture_paid",
        ]
    ],
    "tw",
)
view_sql("wealth_spending")
_ = (money, pct, glossary_help)
