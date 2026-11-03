"""District Profile: a one-page report card for any district (?district=<CDN>, default Eanes ISD)."""

from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from ui import charts, data, maps
from ui.components import (
    FUNCTION_LABELS,
    big_money,
    change_words,
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
from ui.theme import html as html_out

if not require_marts("mart_district_year", "mart_districts", "mart_peers"):
    st.stop()

dl = data.query("district_list")
default = dl[dl.district_name == "EANES ISD"].cdn.iloc[
    0
]  # looked up from the data, never hard-coded
cdn = st.query_params.get("district", default)
if cdn not in set(dl.cdn):
    st.warning(
        f"We don't have a profile for district {html.escape(str(cdn))}, so this page shows Eanes ISD instead."
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
        "Read per-student figures with care.",
        "This district either enrolls many students on virtual campuses or reports enrollment far from its "
        "campus totals. Its per-student numbers don't compare well with other districts, so we leave it out of "
        "the statewide model and the peer comparisons.",
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
    html_out(
        '<div class="ll-caption">'
        + (
            f"Sent {big_money(h.recapture_paid)} to the state in recapture in {sy(latest)}."
            if h.recapture_paid > 0
            else f"Sent no recapture to the state in {sy(latest)}."
        )
        + "</div>"
    )
    link = f"?district={cdn}"
    html_out(
        f'<p class="ll-caption">Link to this profile: <code>/district{html.escape(link)}</code></p>'
    )

with top_l:
    m = st.columns(5)
    with m[0]:
        metric(
            "Spending per student",
            money(h.op_per_student_real),
            f"Texas median {money(h.st_spend)}",
        )
    with m[1]:
        metric(
            "Taxable property per student",
            big_money(h.wealth_per_student_real),
            f"Texas median {big_money(h.st_wealth)}",
        )
    with m[2]:
        metric(
            "Typical household income",
            big_money(h.median_household_income),
            f"Texas median {big_money(h.st_income)}"
            + (" · Census caps this at $250,000" if h.income_topcoded else ""),
        )
    with m[3]:
        metric(
            "Children in poverty",
            pct(h.child_poverty_rate),
            f"Texas median {pct(h.st_poverty)} · Census, 2024",
        )
    with m[4]:
        metric(
            "Students from low-income families",
            pct(h.econ_disadv_pct),
            f"Texas median {pct(h.st_econ)} · TEA, 2023-24",
        )
    if h.predicted_real == h.predicted_real:
        st.markdown(
            md_money(
                f"Based on its wealth, size, students, location type and density, we'd expect this district to "
                f"spend about **{money(h.predicted_real)}** per student. It actually spends "
                f"**{money(h.op_per_student_real)}**, which is "
                f"{abs(h.op_per_student_real / h.predicted_real - 1):.0%} "
                f"{'more' if h.op_per_student_real >= h.predicted_real else 'less'} than expected."
            )
        )

# ---------------------------------------------------------------- spending by function + revenue
rule()
a, b = st.columns([1.5, 1], gap="large")
fn = data.query("district_functions", cdn=cdn)
fn["function_group"] = fn.function_group.map(lambda g: FUNCTION_LABELS.get(g, g))
with a:
    st.subheader("What the money is spent on", anchor=False)
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
        name="similar districts (median)",
        marker=dict(symbol="line-ns", size=18, line=dict(width=3, color=CLAY)),
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title=f"$ per student, {sy(latest)}", tickprefix="$")
    fig.update_layout(legend=dict(orientation="h", y=1.1))
    charts.show(fig, height=380, key="fn")
    reading("Bars show this district. Clay ticks show the median of its 10 most similar districts.")
    view_table(fn, "fn")
    view_sql("district_functions")
with b:
    st.subheader("Where the money comes from", anchor=False)
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
    reading(
        f"Share of all revenue, {sy(latest)}. Local includes property taxes for operations and for debt."
    )
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
    name="middle half of similar districts",
    hoverinfo="skip",
)
fig.add_scatter(
    x=tr.year,
    y=tr.state_median,
    mode="lines",
    line=dict(color=INK_2, dash="dot"),
    name="Texas median",
)
fig.add_scatter(
    x=tr.year,
    y=tr.district,
    mode="lines+markers",
    line=dict(color=CLAY, width=2.4),
    name=nice(h.district_name),
)
fig.update_yaxes(tickprefix="$", title=f"spending per student ({sy(latest)} dollars)")
fig.update_layout(legend=dict(orientation="h", y=1.1))
charts.show(fig, height=360, key="trend")
view_table(tr, "trend")
view_sql("district_trend")

# ---------------------------------------------------------------- peers + fingerprints
rule()
st.subheader("Similar districts and their spending fingerprints", anchor=False)
pe = data.query("district_peers", cdn=cdn)
st.dataframe(
    pe.assign(profile="/district?district=" + pe.cdn),
    hide_index=True,
    width="stretch",
    column_config={
        "wealth_per_student_real": st.column_config.NumberColumn(
            "property per student ($)", format="localized"
        ),
        "op_per_student_real": st.column_config.NumberColumn(
            "spends per student ($)", format="localized"
        ),
        "econ_disadv_pct": st.column_config.NumberColumn("low-income students", format="percent"),
        "recapture_paid": st.column_config.NumberColumn("sent to state ($)", format="localized"),
        "profile": st.column_config.LinkColumn("profile", display_text="open →"),
        "peer_rank": "match",
        "cdn": "district ID",
        "district_name": "district",
    },
)
st.caption(
    "Similar districts are the 10 closest matches on enrollment, property wealth per student and share of "
    "students from low-income families, in the latest year."
)
fp = data.query("peer_fingerprints", cdn=cdn)
fp["petal"] = fp.petal.map(lambda g: FUNCTION_LABELS.get(g, g))
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
    "Each petal is one kind of spending, such as instruction or transportation (labeled on the first glyph). A "
    "longer petal means the district puts a bigger share of its budget there than the typical Texas district. The "
    "gray ring marks the typical share. Petals stop at 3 times the typical share. Similar shapes mean similar budgets."
)
with st.expander("Show the fingerprints as a table"):
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
    fig.add_bar(x=tx.year, y=tx.mo_rate, name="Operations (M&O)", marker_color=INK_2)
    fig.add_bar(x=tx.year, y=tx.is_rate, name="Debt (I&S)", marker_color=CLAY)
    fig.update_layout(
        barmode="stack",
        yaxis_title="rate per $100 of property",
        legend=dict(orientation="h", y=1.1),
    )
    charts.show(fig, height=300, key="tax")
    view_table(tx, "tax")
    view_sql("district_taxes")
with t2:
    st.subheader("Debt owed", anchor=False)
    db = data.query("district_debt", cdn=cdn)
    if db.empty:
        st.caption("This district reports no debt to the Texas Bond Review Board.")
    else:
        fig = go.Figure()
        fig.add_bar(
            x=db.fiscal_year, y=db.cib_principal, name="regular bonds (CIB)", marker_color=INK_2
        )
        fig.add_bar(
            x=db.fiscal_year,
            y=db.cab_principal,
            name="deferred-interest bonds (CAB)",
            marker_color=CLAY,
        )
        fig.add_scatter(
            x=db.fiscal_year,
            y=db.tax_supported_principal,
            mode="lines",
            name="total voter-approved debt",
            line=dict(color="#1B1A17", dash="dot"),
        )
        fig.update_layout(
            barmode="stack",
            yaxis_title="$ borrowed and still owed",
            legend=dict(orientation="h", y=1.12),
        )
        charts.show(fig, height=300, key="debt")
        st.markdown(
            md_money(
                f"In fiscal year {int(h.debt_fy)}, this district owed **{big_money(h.tax_supported_principal)}** in "
                f"voter-approved debt, or **{money(h.debt_per_student)}** per student. "
                + (
                    "None of it is in deferred-interest bonds."
                    if not (h.cab_share_principal > 0)
                    else f"{pct(h.cab_share_principal, 1)} of it is in deferred-interest bonds."
                )
            )
        )
        view_table(db, "debt")
    view_sql("district_debt")
st.info(
    "Bond election history isn't available yet. Our build couldn't reach the Texas Bond Review Board's election search.",
    icon=None,
)

# ---------------------------------------------------------------- growth & building
rule()
st.subheader("Growth and new schools", anchor=False)
g1, g2 = st.columns([1.4, 1], gap="large")
with g1:
    fig = go.Figure(
        go.Scatter(x=tr.year, y=tr.enrollment, mode="lines+markers", line=dict(color=INK_2))
    )
    fig.update_layout(yaxis_title="students enrolled in the fall")
    charts.show(fig, height=260, key="enr")
    st.markdown(
        f"Enrollment **{change_words(h.growth_5y)}** over 5 years and **{change_words(h.growth_10y)}** over 10 years. "
        + (
            "No new campuses have opened since 2016-17."
            if not h.new_campuses_since_2016_17
            else f"**{int(h.new_campuses_since_2016_17)}** "
            f"{'campus has' if int(h.new_campuses_since_2016_17) == 1 else 'campuses have'} opened since 2016-17."
        )
    )
with g2:
    cp = data.query("district_campuses", cdn=cdn)
    if len(cp):
        cp["color"] = [[168, 67, 42, 230] if n else [27, 26, 23, 160] for n in cp.is_new]
        cp = cp.join(
            pd.DataFrame(
                [
                    maps.tip(
                        s.title(), f"Opened in {sy(int(y))}" if n else "Open since at least 2015-16"
                    )
                    for s, y, n in zip(cp.school_name, cp.first_year, cp.is_new, strict=True)
                ],
                index=cp.index,
            )
        )
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
                "default",
                height=260,
            )
        )
        reading("Clay dots are campuses that opened in 2016-17 or later.")
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
