"""District Profile: a one-page report card for any district (?district=<CDN>, default Eanes ISD)."""

from __future__ import annotations

import html

import numpy as np
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from ui import charts, data, maps
from ui.components import (
    big_money,
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
    view_sql,
    view_table,
)
from ui.theme import CLAY, INK_2, RULE

if not require_marts("mart_district_year", "mart_districts", "mart_peers"):
    st.stop()

dl = data.query("district_list")
default = dl[dl.district_name == "EANES ISD"].cdn.iloc[
    0
]  # looked up from the data, never hard-coded
cdn = st.query_params.get("district", default)
if cdn not in set(dl.cdn):
    st.warning(
        f"District {html.escape(str(cdn))} is not in the analysis universe; showing Eanes ISD."
    )
    cdn = default
labels = {
    r.cdn: f"{nice(r.district_name)} · {str(r.county).title()} · {r.cdn}" for r in dl.itertuples()
}
choice = st.selectbox(
    "District", list(labels), index=list(labels).index(cdn), format_func=labels.get
)
if choice != cdn:
    st.query_params["district"] = choice
    st.rerun()
st.query_params["district"] = cdn

h = data.query("district_header", cdn=cdn).iloc[0]
latest = int(h.year)
page_header(
    f"District profile · CDN {cdn}",
    nice(h.district_name),
    f"{str(h.county).title()} · ESC Region {h.esc_region} · {h.locale_detail or h.locale} · "
    f"{h.enrollment:,.0f} students ({sy(latest)})",
)
if h.enrollment_caution:
    notice(
        "Enrollment caution.",
        "TEA reports many students on virtual campuses for this district, or its reported "
        "enrollment differs sharply from its campus totals, so per-student figures are not comparable to other "
        "districts. It is excluded from the statewide model and peer comparisons.",
    )

top_l, top_r = st.columns([2.4, 1], gap="large")
with top_r:
    pin = pdk.Layer(
        "ScatterplotLayer",
        [{"p": [float(h.lon), float(h.lat)]}],
        get_position="p",
        get_radius=14000,
        radius_min_pixels=6,
        get_fill_color=[168, 67, 42, 255],
        stroked=True,
        get_line_color=[27, 26, 23, 255],
        line_width_min_pixels=1.5,
    )
    outline = pdk.Layer(
        "GeoJsonLayer",
        data.geojson("tx_outline"),
        filled=True,
        stroked=True,
        get_fill_color=[236, 230, 217, 255],
        get_line_color=[27, 26, 23, 255],
        line_width_min_pixels=1,
    )
    st.pydeck_chart(
        maps.CompactDeck(
            layers=[outline, pin],
            initial_view_state=pdk.ViewState(latitude=31.2, longitude=-99.4, zoom=3.6),
            map_provider=None,
            map_style=None,
        ),
        height=230,
    )
    rs = "pays recapture" if h.recapture_paid > 0 else "no recapture"
    st.html(
        f'<div class="ll-caption">Locator · {rs} in {sy(latest)}'
        + (f" ({big_money(h.recapture_paid)})" if h.recapture_paid > 0 else "")
        + "</div>"
    )
    link = f"?district={cdn}"
    st.html(f'<p class="ll-caption">Share this view: <code>/district{html.escape(link)}</code></p>')

with top_l:
    m = st.columns(5)
    with m[0]:
        metric(
            "Spending per student",
            money(h.op_per_student_real),
            f"state median {money(h.st_spend)}",
        )
    with m[1]:
        metric(
            "Property wealth / student",
            big_money(h.wealth_per_student_real),
            f"median {big_money(h.st_wealth)}",
        )
    with m[2]:
        metric(
            "Median household income",
            big_money(h.median_household_income),
            f"median {big_money(h.st_income)}" + (" · top-coded" if h.income_topcoded else ""),
        )
    with m[3]:
        metric(
            "Child poverty", pct(h.child_poverty_rate), f"median {pct(h.st_poverty)} · SAIPE 2024"
        )
    with m[4]:
        metric(
            "Econ. disadvantaged", pct(h.econ_disadv_pct), f"median {pct(h.st_econ)} · TAPR 2023-24"
        )
    if h.predicted_real == h.predicted_real:
        st.markdown(
            md_money(
                f"The statewide model predicts **{money(h.predicted_real)}** per student for a district with this wealth, "
                f"size, need, locale and density; actual is **{money(h.op_per_student_real)}** "
                f"(standardized residual {h.std_residual:+.2f})."
            )
        )

# ---------------------------------------------------------------- spending by function + revenue
rule()
a, b = st.columns([1.5, 1], gap="large")
fn = data.query("district_functions", cdn=cdn)
with a:
    st.subheader("Spending by function", anchor=False)
    fig = go.Figure()
    fig.add_bar(
        y=fn.function_group,
        x=fn.district,
        orientation="h",
        name=nice(h.district_name),
        marker_color=INK_2,
    )
    fig.add_scatter(
        y=fn.function_group,
        x=fn.peer_median,
        mode="markers",
        name="peer median",
        marker=dict(symbol="line-ns", size=18, line=dict(width=3, color=CLAY)),
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title=f"real $ per student, {sy(latest)}", tickprefix="$")
    fig.update_layout(legend=dict(orientation="h", y=1.1))
    charts.show(fig, height=380, key="fn")
    reading("Bars: this district. Clay ticks: median of its 10 peers.")
    view_table(fn, "fn")
    view_sql("district_functions")
with b:
    st.subheader("Revenue mix", anchor=False)
    rv = data.query("district_revenue", cdn=cdn)
    r = rv[rv.year == latest].iloc[0]
    fig = go.Figure()
    for lab, val, col in [
        ("Local", r.share_local, INK_2),
        ("State", r.share_state, "#8A8476"),
        ("Federal", r.share_federal, CLAY),
    ]:
        fig.add_bar(
            x=[val],
            y=[""],
            orientation="h",
            name=f"{lab} {val:.0%}",
            marker_color=col,
            text=f"{lab} {val:.0%}",
            textposition="inside",
            insidetextanchor="middle",
        )
    fig.update_layout(barmode="stack", xaxis=dict(tickformat=".0%", range=[0, 1]), showlegend=False)
    charts.show(fig, height=130, key="rev")
    reading(f"Share of all-funds revenue, {sy(latest)}. Local includes M&O and I&S property taxes.")
    view_table(rv, "rev")
    view_sql("district_revenue")

# ---------------------------------------------------------------- trend
rule()
st.subheader(f"Spending per student, {sy(2009)} to {sy(latest)}", anchor=False)
tr = data.query("district_trend", cdn=cdn)
fig = go.Figure()
fig.add_scatter(
    x=list(tr.year) + list(tr.year[::-1]),
    y=list(tr.peer_p75) + list(tr.peer_p25[::-1]),
    fill="toself",
    fillcolor="rgba(92,88,80,0.14)",
    line=dict(width=0),
    name="peer middle 50%",
    hoverinfo="skip",
)
fig.add_scatter(
    x=tr.year,
    y=tr.state_median,
    mode="lines",
    line=dict(color=INK_2, dash="dot"),
    name="state median",
)
fig.add_scatter(
    x=tr.year,
    y=tr.district,
    mode="lines+markers",
    line=dict(color=CLAY, width=2.4),
    name=nice(h.district_name),
)
fig.update_yaxes(tickprefix="$", title=f"real operating $ per student ({sy(latest)} $)")
fig.update_layout(legend=dict(orientation="h", y=1.1))
charts.show(fig, height=360, key="trend")
view_table(tr, "trend")
view_sql("district_trend")

# ---------------------------------------------------------------- peers + fingerprints
rule()
st.subheader("Peers and spending fingerprints", anchor=False)
pe = data.query("district_peers", cdn=cdn)
st.dataframe(
    pe.assign(profile="/district?district=" + pe.cdn),
    hide_index=True,
    width="stretch",
    column_config={
        "wealth_per_student_real": st.column_config.NumberColumn(
            "wealth/student", format="localized"
        ),
        "op_per_student_real": st.column_config.NumberColumn("spend/student", format="localized"),
        "econ_disadv_pct": st.column_config.NumberColumn("econ. dis.", format="percent"),
        "recapture_paid": st.column_config.NumberColumn("recapture", format="localized"),
        "profile": st.column_config.LinkColumn("profile", display_text="open →"),
    },
)
st.caption(
    "Peers: the 10 nearest districts on standardized log enrollment, log property wealth per student and "
    "economically disadvantaged share (latest year)."
)
fp = data.query("peer_fingerprints", cdn=cdn)
order = [cdn] + pe.cdn.tolist()
petals = sorted(fp.petal.unique())
cols = st.columns(6)
for i, c in enumerate(order[:12]):
    g = fp[fp.cdn == c].set_index("petal").reindex(petals)
    f = go.Figure(
        go.Barpolar(
            r=g.ratio.clip(upper=3),
            theta=petals,
            marker_color=CLAY if c == cdn else INK_2,
            marker_line_color="#FBF8F2",
            opacity=0.85,
            hovertemplate="%{theta}: %{r:.2f}× state median share<extra></extra>",
        )
    )
    f.add_trace(
        go.Scatterpolar(
            r=[1] * (len(petals) + 1),
            theta=petals + petals[:1],
            mode="lines",
            line=dict(color=RULE, width=1),
            hoverinfo="skip",
        )
    )
    name = g.district_name.dropna().iloc[0] if g.district_name.notna().any() else c
    f.update_layout(
        showlegend=False,
        title=dict(text=nice(name), font=dict(size=12)),
        margin=dict(t=28, b=4, l=4, r=4),
        polar=dict(
            bgcolor="#F5F1E8",
            radialaxis=dict(visible=False, range=[0, 3]),
            angularaxis=dict(showticklabels=i == 0, tickfont=dict(size=9)),
        ),
    )
    with cols[i % 6]:
        charts.show(f, height=190, key=f"fp_{i}")
reading(
    "Each petal is one function group (labelled on the first glyph); length = the district's share of operating "
    "spending on it relative to the state median share (grey ring = state median, capped at 3×). Similar shapes "
    "mean similar budgets."
)
with st.expander("Fingerprints as a table"):
    st.dataframe(
        fp.pivot_table(index="district_name", columns="petal", values="share").round(3),
        width="stretch",
    )
view_sql("peer_fingerprints", "district_peers")

# ---------------------------------------------------------------- tax and debt
rule()
t1, t2 = st.columns(2, gap="large")
with t1:
    st.subheader("Tax rates", anchor=False)
    tx = data.query("district_taxes", cdn=cdn)
    fig = go.Figure()
    fig.add_bar(x=tx.year, y=tx.mo_rate, name="M&O", marker_color=INK_2)
    fig.add_bar(x=tx.year, y=tx.is_rate, name="I&S (debt)", marker_color=CLAY)
    fig.update_layout(
        barmode="stack", yaxis_title="rate per $100", legend=dict(orientation="h", y=1.1)
    )
    charts.show(fig, height=300, key="tax")
    view_table(tx, "tax")
    view_sql("district_taxes")
with t2:
    st.subheader("Debt outstanding", anchor=False)
    db = data.query("district_debt", cdn=cdn)
    if db.empty:
        st.caption("No outstanding debt reported to the Texas Bond Review Board.")
    else:
        fig = go.Figure()
        fig.add_bar(x=db.fiscal_year, y=db.cib_principal, name="CIB principal", marker_color=INK_2)
        fig.add_bar(x=db.fiscal_year, y=db.cab_principal, name="CAB principal", marker_color=CLAY)
        fig.add_scatter(
            x=db.fiscal_year,
            y=db.tax_supported_principal,
            mode="lines",
            name="tax-supported total",
            line=dict(color="#1B1A17", dash="dot"),
        )
        fig.update_layout(
            barmode="stack",
            yaxis_title="$ principal outstanding",
            legend=dict(orientation="h", y=1.12),
        )
        charts.show(fig, height=300, key="debt")
        st.markdown(
            md_money(
                f"FY{int(h.debt_fy)}: **{big_money(h.tax_supported_principal)}** tax-supported, "
                f"**{money(h.debt_per_student)}** per student; CAB share {pct(h.cab_share_principal, 1)}."
            )
        )
        view_table(db, "debt")
    view_sql("district_debt")
st.info(
    "Bond election history is not available yet (BRB election search not reachable from the build).",
    icon=None,
)

# ---------------------------------------------------------------- growth & building
rule()
st.subheader("Growth and building", anchor=False)
g1, g2 = st.columns([1.4, 1], gap="large")
with g1:
    fig = go.Figure(
        go.Scatter(x=tr.year, y=tr.enrollment, mode="lines+markers", line=dict(color=INK_2))
    )
    fig.update_layout(yaxis_title="fall enrollment")
    charts.show(fig, height=260, key="enr")
    st.markdown(
        f"5-year change **{pct(h.growth_5y)}**, 10-year **{pct(h.growth_10y)}**; "
        f"**{int(h.new_campuses_since_2016_17 or 0)}** campuses opened since 2016-17 and still open."
    )
with g2:
    cp = data.query("district_campuses", cdn=cdn)
    if len(cp):
        cp["color"] = [[168, 67, 42, 230] if n else [27, 26, 23, 160] for n in cp.is_new]
        cp["tip"] = [
            f"{html.escape(s.title())} (first listed {sy(int(y))})"
            for s, y in zip(cp.school_name, cp.first_year, strict=True)
        ]
        st.pydeck_chart(
            maps.deck(
                [
                    pdk.Layer(
                        "ScatterplotLayer",
                        cp,
                        get_position=["lon", "lat"],
                        get_radius=250,
                        radius_min_pixels=4,
                        get_fill_color="color",
                        pickable=True,
                    )
                ],
                pdk.ViewState(
                    latitude=float(cp.lat.mean()), longitude=float(cp.lon.mean()), zoom=9.5
                ),
                "{tip}",
                height=260,
            )
        )
        reading("Campuses: clay = opened 2016-17 or later.")
    view_sql("district_campuses")

rule()
csv = data.query("district_trend", cdn=cdn).merge(
    data.query("district_revenue", cdn=cdn), on="year", how="left"
)
st.download_button(
    "Download this district's data (CSV)",
    csv.to_csv(index=False),
    file_name=f"district_{cdn}.csv",
    mime="text/csv",
)
_ = np
