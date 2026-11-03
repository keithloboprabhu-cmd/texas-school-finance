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
        help="Small districts have scale diseconomies and noisy per-student figures.",
    )
    color_by = st.segmented_control(
        "Colour", ["Econ. disadvantaged %", "Locale"], default="Econ. disadvantaged %"
    )
with c3:
    st.caption(
        "Denominator: fall enrollment. ADA and WADA are not available in bulk for every district "
        "(TEA's Summary of Finances has no statewide download). Cost adjustment: not applied "
        "(see Methodology)."
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
        f'<div class="ll-kicker">{term("elasticity", "Wealth elasticity of spending")}, {sy(year)}</div>'
    )
    html_out(
        f'<div class="ll-metric"><div class="value">{b:+.3f}</div>'
        f'<div class="label">95% CI {lo:+.3f} to {hi:+.3f} · R² {r2:.2f} · n = {n:,}</div></div>'
    )
    st.markdown(
        f"A district with **10% more property wealth per student spends about {b * 10:+.2f}% more** per student "
        f"(95% CI {lo * 10:+.2f}% to {hi * 10:+.2f}%). Zero would mean spending does not depend on wealth."
    )
    st.caption(
        f"Enrollment-weighted least squares of log spending on log wealth, robust (HC1) errors. "
        f"Excludes {len(flagged)} districts flagged for large virtual or non-resident enrollment"
        + (", and districts under 500 students." if hide_small else ".")
    )
    if year == latest:
        coefs = data.query("model_latest")
        cw = coefs[(coefs.model == "controlled") & (coefs.term == "log_wealth")].iloc[0]
        st.markdown(
            f"**With controls** (size, need, locale, density): **{cw.coef:+.3f}** "
            f"(95% CI {cw.ci_lo:+.3f} to {cw.ci_hi:+.3f})."
        )
        with st.expander("Controlled model coefficients"):
            st.dataframe(
                coefs[coefs.model.isin(["controlled", "huber"])][
                    ["model", "term", "coef", "ci_lo", "ci_hi", "p_value", "n"]
                ].round(4),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Controlled: WLS, enrollment weights, HC1 errors. Huber: robust regression sensitivity check. "
                "Demographic shares are TAPR 2023-24. Locale baseline: City."
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
                colorbar=dict(title="econ. dis.", tickformat=".0%", thickness=10),
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
    fig.update_xaxes(type="log", title=f"Property wealth per student ({sy(latest)} $, log scale)")
    fig.update_yaxes(type="log", title=f"Operating spending per student ({sy(latest)} $, log)")
    fig.update_layout(legend=dict(orientation="h", y=1.05))
    charts.show(fig, height=560, key="ws_scatter")
    reading(
        "Each dot is a district, sized by enrollment. A flat clay line means spending does not rise with wealth."
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
st.subheader(f"Outliers after controls, {sy(latest)}", anchor=False)
html_out(
    f'<p class="ll-reading">Ranked by standardized residual from the controlled model: how far actual spending '
    f'sits from what wealth, size, need, locale and density predict. "Why it might be" hints use only this '
    f"project's data. ⚑ = ranking changes under {term('huber', 'Huber robust regression')}.</p>"
)
ol = data.query("outliers_latest")


def outlier_table(sub: pd.DataFrame, key: str):
    t = sub.assign(
        district=sub.district_name.map(nice) + np.where(sub.method_sensitive, " ⚑", ""),
        actual=sub.op_per_student_real,
        predicted=sub.predicted_real,
        recapture=np.where(sub.recapture_paid > 0, "pays", ""),
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
            "actual": st.column_config.NumberColumn("actual $/student", format="localized"),
            "predicted": st.column_config.NumberColumn("predicted", format="localized"),
            "std_residual": st.column_config.NumberColumn("std. residual", format="%.2f"),
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
    f'<p class="ll-reading">{term("property_wealth", "Property wealth")} is the tax base; household income is '
    "the community. Where they diverge, a district can be property-rich but income-poor (mineral or "
    "industrial value) or the reverse.</p>"
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
fig.update_xaxes(type="log", title="Property wealth per student (log)")
fig.update_yaxes(title="Median household income (ACS 2020-2024)", tickprefix="$")
fig.update_layout(legend=dict(orientation="h", y=1.08))
charts.show(fig, height=460, key="two_wealths")
pr = tw[tw.quadrant == "property-rich, income-poor"]
st.markdown(
    f"**{len(pr)} districts** are above the state median in property wealth but below it in household "
    f"income; {int((pr.recapture_paid > 0).sum())} of them paid recapture in {sy(latest)}."
)
reading("Quadrant lines are the district medians. Income is top-coded by the Census at $250,000.")
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
