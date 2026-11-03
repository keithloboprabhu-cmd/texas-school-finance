"""Atlas (home): the Texas map, layer switcher, overlays, findings strip and guided tour."""

from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from ui import charts, data, maps, tour
from ui.components import (
    big_money,
    legend_bivariate,
    legend_diverging,
    legend_quantile,
    money,
    nice,
    page_header,
    pct,
    reading,
    require_marts,
    rule,
    sy,
    view_sql,
    view_table,
)
from ui.theme import DIVERGING_7, INK_2, SEQUENTIAL_7
from ui.theme import html as html_out

if not require_marts("mart_district_year", "mart_districts", "mart_equity_state_year"):
    st.stop()

qp = st.query_params
years = data.query("meta_years").year.tolist()
latest = years[-1]
LAYERS = data.config("metrics")["layers"]
VIEWS = ["Bivariate", "Single metric", "3D Wealth Relief"]

page_header(
    "Lone Star Ledger · Texas School Finance Atlas",
    "Where the money goes in Texas schools",
    "Property wealth, spending, recapture, debt and growth for every Texas school district. "
    "Click a district to see its numbers.",
)

# ---------------------------------------------------------------- tour state
if "tour" in qp and "tour_step" not in st.session_state:
    st.session_state.tour_step = int(qp["tour"])
tour_on = "tour_step" in st.session_state
stops = tour.stops(latest) if tour_on else []
stop = stops[st.session_state.tour_step] if tour_on else None

# ---------------------------------------------------------------- controls
c1, c2, c3, c4 = st.columns([0.9, 1.9, 2, 1.3])
with c1:
    year = st.selectbox(
        "School year",
        years[::-1],
        format_func=sy,
        index=years[::-1].index(int(qp.get("year", latest))) if qp.get("year") else 0,
    )
with c2:
    view = (
        st.segmented_control(
            "View",
            VIEWS,
            default=stop["view"] if stop else qp.get("view", "Bivariate"),
            key=f"view_{st.session_state.get('tour_step', 'x')}",
        )
        or "Bivariate"
    )
metric_keys = list(LAYERS)
with c3:
    disabled = view != "Single metric"
    default_metric = stop["metric"] if stop else qp.get("metric", "wealth")
    metric = st.selectbox(
        "Layer",
        metric_keys,
        index=metric_keys.index(default_metric if default_metric in LAYERS else "wealth"),
        format_func=lambda k: f"{LAYERS[k]['theme']} · {LAYERS[k]['label']}",
        disabled=disabled,
        key=f"metric_{st.session_state.get('tour_step', 'x')}",
    )
with c4:
    overlays = st.multiselect(
        "Overlays",
        ["Counties", "ESC regions", "Metro areas", "All campuses", "New campuses since 2016-17"],
        default=["Counties"],
    )
st.query_params.update({"year": str(year), "view": view, "metric": metric})

df = data.query("atlas_layers", year=year)
names = df.sort_values("district_name")
search = st.selectbox(
    "Find a district",
    ["(all of Texas)"] + names.district_name.map(nice).tolist(),
    help="Type to search; the map flies to the district.",
)

# ---------------------------------------------------------------- colours
fmt_map = {
    "money": money,
    "money_k": lambda v: "n/a" if pd.isna(v) else f"${v / 1000:,.0f}K",
    "pct": pct,
    "rate": lambda v: "n/a" if pd.isna(v) else f"{v:.4f}",
    "num": lambda v: "n/a" if pd.isna(v) else f"{v:,.1f}",
}
legend_note = ""
if view == "Bivariate":
    fill, wt, stt = maps.bivariate_colors(df.wealth_per_student, df.op_per_student)
    df["fill"] = fill
elif view == "3D Wealth Relief":
    med = df.op_per_student.median()
    df["fill"] = maps.diverging_colors(df.op_per_student, med)
    cap = df.wealth_per_student.quantile(0.99)
    df["elev"] = df.wealth_per_student.clip(upper=cap).fillna(0) / cap * 120_000
    legend_note = f"Height capped at the 99th percentile ({fmt_map['money_k'](cap)} per student)."
else:
    spec = LAYERS[metric]
    col = df[spec["column"]].astype(float)
    if spec["palette"] == "diverging":
        center = col.median() if metric == "spending" else 0.0
        df["fill"] = maps.diverging_colors(col, center)
    elif spec["palette"] == "diverging_zero":
        df["fill"] = maps.diverging_colors(col, 0.0)
    else:
        nonzero = col.where(col > 0) if metric in ("recapture", "new_campuses", "cab") else col
        breaks = maps.quantile_breaks(nonzero)
        df["fill"] = maps.class_colors(maps.classify(nonzero, breaks), SEQUENTIAL_7)

df["tip"] = [
    f"<b>{html.escape(nice(r.district_name))}</b><br/>{html.escape(str(r.county).title())} · "
    f"{'' if pd.isna(r.enrollment) else f'{r.enrollment:,.0f} students'}<br/>"
    f"Wealth/student {fmt_map['money_k'](r.wealth_per_student)}<br/>"
    f"Spending/student {money(r.op_per_student)}<br/>"
    + (
        f"{LAYERS[metric]['label']}: {fmt_map[LAYERS[metric]['fmt']](getattr(r, LAYERS[metric]['column']))}"
        if view == "Single metric"
        else ""
    )
    for r in df.itertuples()
]

geo = maps.features_with(
    data.geojson("tx_districts_simplified"),
    df,
    ["cdn", "district_name", "fill", "tip"] + (["elev"] if "elev" in df else []),
)
for f in geo["features"]:
    f["tip"] = f["properties"].pop("tip")  # deck.gl tooltips read top-level keys; keep one copy

layers = []
if view == "3D Wealth Relief":
    layers.append(
        pdk.Layer(
            "GeoJsonLayer",
            geo,
            id="districts",
            pickable=True,
            extruded=True,
            wireframe=False,
            get_elevation="properties.elev",
            get_fill_color="properties.fill",
            get_line_color=[251, 248, 242, 120],
            auto_highlight=True,
            highlight_color=[168, 67, 42, 160],
        )
    )
else:
    layers.append(
        pdk.Layer(
            "GeoJsonLayer",
            geo,
            id="districts",
            pickable=True,
            stroked=True,
            filled=True,
            get_fill_color="properties.fill",
            get_line_color=[251, 248, 242, 200],
            line_width_min_pixels=0.4,
            auto_highlight=True,
            highlight_color=[168, 67, 42, 120],
        )
    )
if "Counties" in overlays:
    layers.append(
        maps.overlay_layer(data.geojson("tx_counties"), "counties", (27, 26, 23, 70), 0.6)
    )
if "ESC regions" in overlays:
    layers.append(maps.overlay_layer(data.geojson("tx_esc_regions"), "esc", (27, 26, 23, 200), 1.6))
if "Metro areas" in overlays:
    layers.append(maps.overlay_layer(data.geojson("tx_metros"), "metros", (168, 67, 42, 200), 1.4))
if "All campuses" in overlays or "New campuses since 2016-17" in overlays:
    camp = data.query("campus_points")
    if "New campuses since 2016-17" in overlays and "All campuses" not in overlays:
        camp = camp[camp.is_new]
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            camp,
            id="campuses",
            get_position=["lon", "lat"],
            get_radius=900,
            radius_min_pixels=1.5,
            radius_max_pixels=5,
            get_fill_color="color",
            pickable=False,
        )
    )
layers.append(
    pdk.Layer(
        "GeoJsonLayer",
        data.geojson("tx_outline"),
        id="outline",
        filled=False,
        stroked=True,
        get_line_color=[27, 26, 23, 255],
        line_width_min_pixels=1.4,
    )
)

# camera
view_state = maps.TX_VIEW
if search != "(all of Texas)":
    r = df[df.district_name.map(nice) == search].iloc[0]
    view_state = pdk.ViewState(
        latitude=r.lat,
        longitude=r.lon,
        zoom=8.6,
        pitch=45 if view.startswith("3D") else 0,
        transition_duration=1500,
    )
elif stop and stop.get("focus"):
    lat, lon, z = stop["focus"]
    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=z, transition_duration=1500)
elif view.startswith("3D"):
    view_state = pdk.ViewState(
        latitude=30.4, longitude=-99.0, zoom=5.2, pitch=48, bearing=-12, transition_duration=1500
    )

left, right = st.columns([3.1, 1], gap="large")
with left:
    event = st.pydeck_chart(
        maps.deck(layers, view_state, "{tip}", height=640),
        on_select="rerun",
        selection_mode="single-object",
        key=f"atlas_{view}_{metric}_{year}",
    )
    html_out(
        '<div class="ll-source">N ↑ · Web Mercator, scale varies with latitude · Sources: TEA PEIMS, Comptroller '
        "certified values, Census SAIPE/ACS, NCES EDGE, Texas Bond Review Board · Data as of "
        f"{sy(latest)} (spending), FY{int(data.query('debt_state_year').fiscal_year.max())} (debt) · Basemap © CARTO, © OpenStreetMap</div>"
    )

with right:
    if view == "Bivariate":
        legend_bivariate()
        reading(
            "Districts with the same colour sit in the same third of Texas for both wealth and spending."
        )
    elif view == "3D Wealth Relief":
        legend_diverging("Spending per student vs. state median", "below median", "above median")
        reading(
            "Height = property wealth per student. Tall teal ridges are wealthy districts that spend "
            "below the median. " + legend_note
        )
    else:
        spec = LAYERS[metric]
        if spec["palette"].startswith("diverging"):
            legend_diverging(spec["label"], "lower", "higher")
        else:
            col = df[spec["column"]].astype(float)
            nz = col.where(col > 0) if metric in ("recapture", "new_campuses", "cab") else col
            legend_quantile(spec["label"], maps.quantile_breaks(nz), fmt_map[spec["fmt"]])
        reading(spec["read"])

    sel = None
    try:
        objs = event.selection["objects"].get("districts", [])
        if objs:
            sel = objs[0].get("properties", objs[0]).get("cdn")
    except (AttributeError, KeyError, TypeError):
        sel = None
    if sel is None and search != "(all of Texas)":
        sel = df[df.district_name.map(nice) == search].cdn.iloc[0]
    if sel:
        r = df[df.cdn == sel].iloc[0]
        html_out(
            f'<div class="ll-panel"><div class="ll-kicker">Selected</div>'
            f'<h3 style="margin:0.2rem 0">{html.escape(nice(r.district_name))}</h3>'
            f'<div class="ll-caption">{html.escape(str(r.county).title())} · ESC Region {r.esc_region} · {r.locale}</div></div>'
        )
        for label, val in [
            ("Students", f"{r.enrollment:,.0f}" if pd.notna(r.enrollment) else "n/a"),
            ("Spending per student", money(r.op_per_student)),
            ("Property wealth per student", fmt_map["money_k"](r.wealth_per_student)),
            ("Median household income", fmt_map["money_k"](r.median_household_income)),
            ("Recapture paid", big_money(r.recapture_paid)),
        ]:
            st.markdown(f"**{label}**  \n`{val}`")
        st.page_link(
            "app_pages/district.py", label="Open full profile →", query_params={"district": sel}
        )
    else:
        st.caption("Click a district, or search above, to see its numbers here.")

    with st.expander("Take the tour" if not tour_on else "Tour", expanded=tour_on):
        if not tour_on:
            if st.button("Start the guided tour", type="primary"):
                st.session_state.tour_step = 0
                st.rerun()
        else:
            i = st.session_state.tour_step
            s = stops[i]
            html_out(
                f'<div class="ll-tourcard"><div class="step">Stop {i + 1} of {len(stops)}</div>'
                f'<h3 style="margin:0.2rem 0">{html.escape(s["title"])}</h3><p>{html.escape(s["text"])}</p>'
                f'<div class="big">{html.escape(s["number"])}</div>'
                f'<div class="ll-caption">{html.escape(s["number_label"])}</div></div>'
            )
            b1, b2, b3 = st.columns(3)
            if b1.button("← Prev", disabled=i == 0):
                st.session_state.tour_step -= 1
                st.query_params["tour"] = str(st.session_state.tour_step)
                st.rerun()
            if b2.button("Next →", disabled=i == len(stops) - 1):
                st.session_state.tour_step += 1
                st.query_params["tour"] = str(st.session_state.tour_step)
                st.rerun()
            if b3.button("End"):
                del st.session_state.tour_step
                st.query_params.pop("tour", None)
                st.rerun()

view_table(
    df[
        [
            "cdn",
            "district_name",
            "county",
            "enrollment",
            "wealth_per_student",
            "op_per_student",
            "median_household_income",
            "recapture_paid",
            "debt_per_student",
            "growth_5y",
            "child_poverty_rate",
        ]
    ].sort_values("district_name"),
    "atlas",
    label="View map as table",
    column_config={
        "wealth_per_student": st.column_config.NumberColumn(format="localized"),
        "op_per_student": st.column_config.NumberColumn(format="localized"),
        "recapture_paid": st.column_config.NumberColumn(format="localized"),
        "debt_per_student": st.column_config.NumberColumn(format="localized"),
        "growth_5y": st.column_config.NumberColumn(format="percent"),
        "child_poverty_rate": st.column_config.NumberColumn(format="percent"),
    },
)
view_sql("atlas_layers")

# ---------------------------------------------------------------- findings strip
rule()
st.subheader("Three findings", anchor=False)
eq = data.query("findings")
first, last = eq.iloc[0], eq.iloc[-1]
out = data.query("finding_outliers")
over = out[out.direction == "over"].iloc[0]
rec = data.query("finding_recapture", year=latest).iloc[0]

f1, f2, f3 = st.columns(3, gap="large")
with f1:
    html_out(
        '<div class="ll-finding"><div class="num">01</div><p>In '
        f"{sy(int(last.year))}, property wealth barely predicts operating spending per student: a district with 10% "
        f"more wealth per student spends about <b>{last.elasticity * 10:+.2f}%</b> more (95% CI "
        f"{last.elasticity_lo * 10:+.2f}% to {last.elasticity_hi * 10:+.2f}%). In {sy(int(first.year))} it was "
        f"{first.elasticity * 10:+.2f}%.</p></div>"
    )
    fig = go.Figure()
    fig.add_scatter(x=eq.year, y=eq.elasticity, mode="lines+markers", line=dict(color=INK_2))
    fig.add_scatter(
        x=list(eq.year) + list(eq.year[::-1]),
        y=list(eq.elasticity_hi) + list(eq.elasticity_lo[::-1]),
        fill="toself",
        fillcolor="rgba(92,88,80,0.15)",
        line=dict(width=0),
        hoverinfo="skip",
    )
    fig.add_hline(y=0, line=dict(color=DIVERGING_7[0], width=1, dash="dot"))
    fig.update_layout(showlegend=False, yaxis_title="elasticity", margin=dict(t=10))
    charts.show(fig, height=180, key="f1")
    st.page_link("app_pages/wealth_spending.py", label="Explore →")
with f2:
    html_out(
        '<div class="ll-finding"><div class="num">02</div><p>'
        f"All <b>{int(over.n_small)} of the {int(over.n)}</b> districts that spend most above prediction have fewer than "
        f"500 students (median {over.median_enrollment:,.0f}); they spend {money(over.median_actual)} per student "
        f"against {money(over.median_predicted)} predicted. Statewide, {pct(over.share_small_statewide, 0)} of "
        "districts are that small.</p></div>"
    )
    ol = data.query("outliers_latest")
    fig = go.Figure(
        go.Scatter(
            x=ol.enrollment,
            y=ol.std_residual,
            mode="markers",
            marker=dict(size=5, color=np.where(ol.direction.eq("over"), "#A8432A", "#B9B2A3")),
        )
    )
    fig.update_xaxes(type="log", title="students (log)")
    fig.update_layout(yaxis_title="std. residual", margin=dict(t=10))
    charts.show(fig, height=180, key="f2")
    st.page_link("app_pages/wealth_spending.py", label="Explore →")
with f3:
    html_out(
        '<div class="ll-finding"><div class="num">03</div><p>'
        f"Districts paid <b>{big_money(rec.total_paid)}</b> in recapture in {sy(latest)}. "
        f"{big_money(rec.paid_by_mineral_majority)} ({rec.paid_by_mineral_majority / rec.total_paid:.0%}) came from "
        f"{int(rec.payers_mineral_majority)} districts where minerals are most of the tax base, and "
        f"{int(rec.payers_below_median_income)} of the {int(rec.payers)} payers have below-median household income.</p></div>"
    )
    ry = data.query("recapture_by_year")
    fig = go.Figure(go.Bar(x=ry.year, y=ry.recapture_real / 1e9, marker_color=INK_2))
    fig.update_layout(yaxis_title=f"$B ({sy(latest)} $)", margin=dict(t=10))
    charts.show(fig, height=180, key="f3")
    st.page_link("app_pages/recapture.py", label="Explore →")
view_sql("findings", "finding_outliers", "finding_recapture", "recapture_by_year")
