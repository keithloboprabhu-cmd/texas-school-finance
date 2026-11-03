"""Recapture: districts that send excess local revenue to the state."""

from __future__ import annotations

import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from ui import charts, data, maps
from ui.components import (
    big_money,
    md_money,
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
from ui.theme import CLAY, INK_2
from ui.theme import html as html_out

if not require_marts("mart_recapture", "mart_money_cycle_state_year"):
    st.stop()

years = data.query("meta_years").year.tolist()
page_header(
    "02 · Robin Hood",
    "Recapture",
    "Which districts send local property-tax revenue to the state, and how much.",
)
html_out(
    f'<p class="ll-subtitle" style="margin-top:0">How it works: Texas sets how much revenue each district is '
    f"entitled to from its local taxes and state aid. A property-wealthy district whose local M&O taxes would raise "
    f"more than that entitlement sends the excess to the state, which uses it in the Foundation School Program "
    f"({term('recapture', 'recapture')}, Texas Education Code chapter 49). It is a payment into a state pool, not a "
    f'transfer to particular districts. <a href="https://tea.texas.gov/about-tea/state-funding/excess-local-revenue">'
    f"TEA's explainer →</a></p>"
)
year = st.selectbox("School year", years[::-1], format_func=sy)

rd = data.query("recapture_districts", year=year)
ry = data.query("recapture_by_year")
row = ry[ry.year == year].iloc[0]
m1, m2, m3, m4 = st.columns(4)
from ui.components import metric  # noqa: E402

with m1:
    metric("Recapture paid", big_money(row.recapture_paid), sy(year))
with m2:
    metric("Districts paying", f"{int(row.payers):,}")
with m3:
    metric(
        "Largest payer",
        nice(rd.district_name.iloc[0]) if len(rd) else "n/a",
        big_money(rd.recapture_paid.iloc[0]) if len(rd) else "",
    )
with m4:
    metric(
        "Median share of spending",
        pct(rd.share_of_spending.median(), 1),
        "recapture / (operating + recapture)",
    )

rule()
left, right = st.columns([2.2, 1], gap="large")
with left:
    st.subheader("Recapture flow map", anchor=False)
    rd2 = rd.dropna(subset=["lat"]).copy()
    mx = rd2.recapture_paid.max()
    rd2["w"] = 0.6 + 7 * (rd2.recapture_paid / mx) ** 0.5
    rd2["tip"] = [
        f"<b>{nice(n)}</b><br/>{money(p)} paid<br/>{money(s)} per student"
        for n, p, s in zip(
            rd2.district_name, rd2.recapture_paid, rd2.recapture_per_student_real, strict=True
        )
    ]
    rd2["path"] = [
        maps.flat_arc((lon, lat), maps.CAPITOL) for lon, lat in zip(rd2.lon, rd2.lat, strict=True)
    ]
    rd2 = rd2.sort_values("recapture_paid")  # draw the largest flows on top
    arcs = pdk.Layer(
        "PathLayer",
        rd2,
        id="arcs",
        get_path="path",
        get_width="w",
        width_units="'pixels'",
        width_max_pixels=8,
        width_min_pixels=0.5,
        get_color=[168, 67, 42, 150],
        cap_rounded=True,
        pickable=True,
    )
    dots = pdk.Layer(
        "ScatterplotLayer",
        rd2,
        id="payers",
        get_position=["lon", "lat"],
        get_radius=2500,
        radius_min_pixels=2,
        get_fill_color=[27, 26, 23, 200],
        pickable=True,
    )
    capitol = pdk.Layer(
        "TextLayer",
        [{"p": list(maps.CAPITOL), "t": "State Capitol"}],
        get_position="p",
        get_text="t",
        get_size=13,
        get_color=[27, 26, 23, 255],
        get_alignment_baseline="'top'",
        get_pixel_offset=[0, 8],
        font_family="'Inter Tight'",
    )
    outline = maps.overlay_layer(data.geojson("tx_outline"), "outline", (27, 26, 23, 255), 1.2)
    st.pydeck_chart(
        maps.deck(
            [outline, arcs, dots, capitol],
            pdk.ViewState(latitude=31.1, longitude=-99.4, zoom=4.75, pitch=20),
            "{tip}",
            height=560,
        )
    )
    reading(
        "Payments to the state's Foundation School Program. Each arc runs from a paying district to the State "
        "Capitol; width grows with dollars paid. Recapture goes into a state pool, not to particular districts."
    )
    view_table(
        rd[
            [
                "cdn",
                "district_name",
                "county",
                "enrollment",
                "recapture_paid",
                "recapture_per_student_real",
                "share_of_spending",
            ]
        ],
        "flow",
    )
    view_sql("recapture_districts")
with right:
    st.subheader("By year", anchor=False)
    fig = go.Figure(
        go.Bar(
            x=ry.year,
            y=ry.recapture_real / 1e9,
            marker_color=[CLAY if y == year else INK_2 for y in ry.year],
            hovertemplate="%{x}: $%{y:.2f}B<extra></extra>",
        )
    )
    fig.update_layout(yaxis_title=f"$ billions ({sy(years[-1])} dollars)")
    charts.show(fig, height=300, key="ry")
    rec = data.query("recapture_recent")
    if len(rec):
        st.caption(
            md_money(
                "TEA also reports "
                + "; ".join(
                    f"{big_money(r.recapture_paid)} for {sy(int(r.year))} ({r.amount_status})"
                    for r in rec.itertuples()
                )
                + ". Not shown above until final."
            )
        )
    view_table(ry, "ry")
    view_sql("recapture_by_year", "recapture_recent")
    grp = data.query("recapture_by_group", year=year)
    st.markdown("**By locale**")
    st.dataframe(
        grp[grp.kind == "locale"][["grp", "payers", "paid"]],
        hide_index=True,
        width="stretch",
        column_config={"paid": st.column_config.NumberColumn(format="localized"), "grp": "locale"},
    )
    with st.expander("By ESC region"):
        st.dataframe(
            grp[grp.kind == "region"][["grp", "payers", "paid"]],
            hide_index=True,
            width="stretch",
            column_config={
                "paid": st.column_config.NumberColumn(format="localized"),
                "grp": "region",
            },
        )
    view_sql("recapture_by_group")

# ---------------------------------------------------------------- money cycle
rule()
st.subheader(f"The money cycle, {sy(year)}", anchor=False)
mc = data.query("money_cycle", year=year).iloc[0]
src = [
    ("Local M&O tax", mc.local_mo_tax),
    ("Local I&S (debt) tax", mc.local_is_tax),
    ("Other local", mc.other_local),
    ("State aid", mc.state_revenue),
    ("Federal", mc.federal_revenue),
]
uses = [
    ("Recapture to state", mc.recapture),
    ("Debt service", mc.debt_service),
    ("Capital & construction", mc.capital),
    ("Instruction", mc.op_instruction + mc.op_instructional_support),
    (
        "Leadership & admin",
        mc.op_school_leadership + mc.op_general_administration + mc.op_data_processing,
    ),
    ("Student support", mc.op_student_support),
    (
        "Transport, food, extracurricular",
        mc.op_transportation + mc.op_food_service + mc.op_extracurricular,
    ),
    ("Plant & security", mc.op_plant_maintenance_security),
    ("Other (community, intergovernmental)", mc.op_community_services + mc.intergovernmental),
]
tot_src, tot_use = sum(v for _, v in src), sum(v for _, v in uses)
labels = (
    [f"{n}<br>{big_money(v)} · {v / tot_src:.0%}" for n, v in src]
    + [f"Texas ISDs<br>{big_money(tot_src)}"]
    + [f"{n}<br>{big_money(v)} · {v / tot_use:.0%}" for n, v in uses]
)
hub = len(src)
fig = go.Figure(
    go.Sankey(
        arrangement="snap",
        textfont=dict(color="#1B1A17", size=13, family="Inter Tight"),
        node=dict(
            label=labels,
            pad=14,
            thickness=14,
            color=["#5C5850"] * len(src) + ["#1B1A17"] + [CLAY] + ["#8A8476"] * (len(uses) - 1),
            line=dict(width=0),
        ),
        link=dict(
            source=list(range(hub)) + [hub] * len(uses),
            target=[hub] * hub + list(range(hub + 1, hub + 1 + len(uses))),
            value=[v for _, v in src] + [v for _, v in uses],
            color="rgba(92,88,80,0.18)",
        ),
    )
)
fig.update_layout(font=dict(size=13))
charts.show(fig, height=520, key="sankey")
reading(
    f"Revenue recorded by districts (left) and what they spent it on (right), all funds, nominal dollars. "
    f"Sources total {big_money(tot_src)} and uses {big_money(tot_use)}; the gap is changes in fund balance and "
    "financing (bond proceeds pay for much of the capital)."
)
view_table(
    data.query("money_cycle", year=year)
    .T.reset_index()
    .rename(columns={"index": "item", 0: "dollars"}),
    "mc",
)
view_sql("money_cycle")

# ---------------------------------------------------------------- tables
rule()
t1, t2 = st.columns(2, gap="large")
cfg = {
    "recapture_paid": st.column_config.NumberColumn("paid", format="localized"),
    "recapture_per_student_real": st.column_config.NumberColumn("per student", format="localized"),
    "share_of_spending": st.column_config.NumberColumn("share of spending", format="percent"),
}
with t1:
    st.subheader("Top 20 by dollars", anchor=False)
    st.dataframe(
        rd.nlargest(20, "recapture_paid")[
            [
                "district_name",
                "county",
                "enrollment",
                "recapture_paid",
                "recapture_per_student_real",
            ]
        ],
        hide_index=True,
        width="stretch",
        column_config=cfg,
    )
with t2:
    st.subheader("Top 20 by per-student burden", anchor=False)
    st.dataframe(
        rd.nlargest(20, "recapture_per_student_real")[
            [
                "district_name",
                "county",
                "enrollment",
                "recapture_per_student_real",
                "share_of_spending",
            ]
        ],
        hide_index=True,
        width="stretch",
        column_config=cfg,
    )
view_sql("recapture_districts")

with st.expander("TEA excess local revenue lists (2025-26 and 2026-27 estimates)"):
    st.caption(
        "TEA's July notification lists. Estimates; districts on the list do not necessarily owe recapture."
    )
    st.dataframe(data.query("elr_list"), hide_index=True, width="stretch")
    view_sql("elr_list")
