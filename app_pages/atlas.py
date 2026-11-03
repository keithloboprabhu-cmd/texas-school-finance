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
    explained_words,
    legend_bivariate,
    legend_diverging,
    legend_quantile,
    money,
    more_less,
    nice,
    page_header,
    pct,
    per10,
    reading,
    require_marts,
    rule,
    share_words,
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
VIEWS = ["Bivariate", "Single metric", "3D Wealth Relief"]  # internal keys (also used in URLs)
VIEW_LABELS = {
    "Bivariate": "Combined",
    "Single metric": "One measure",
    "3D Wealth Relief": "3D Wealth Relief",
}

page_header(
    "Atlas · Texas school districts",
    "Where the money goes in Texas schools",
    "Compare property wealth, spending, debt and growth across every Texas school district. "
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
            "Map view",
            VIEWS,
            format_func=VIEW_LABELS.get,
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
        "Measure (for the One measure view)",
        metric_keys,
        index=metric_keys.index(default_metric if default_metric in LAYERS else "wealth"),
        format_func=lambda k: f"{LAYERS[k]['theme']} · {LAYERS[k]['label']}",
        disabled=disabled,
        key=f"metric_{st.session_state.get('tour_step', 'x')}",
    )
with c4:
    overlays = st.multiselect(
        "Also show",
        ["Counties", "ESC regions", "Metro areas", "All campuses", "New campuses since 2016-17"],
        default=["Counties"],
    )
st.query_params.update({"year": str(year), "view": view, "metric": metric})

df = data.query("atlas_layers", year=year)
names = df.sort_values("district_name")
search = st.selectbox(
    "Find a district",
    ["(all of Texas)"] + names.district_name.map(nice).tolist(),
    help="Type a district name. The map zooms to it.",
)

# ---------------------------------------------------------------- colours
fmt_map = {
    "money": money,
    "money_k": big_money,
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
    legend_note = (
        f"The tallest 1% of districts are cut off at {fmt_map['money_k'](cap)} per student "
        "so the rest stay visible."
    )
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

med_spend = df.op_per_student.median()


def metric_line(r) -> str:
    """Plain-English line for the selected single-metric layer."""
    v = getattr(r, LAYERS[metric]["column"])
    if pd.isna(v):
        return f"{LAYERS[metric]['label']}: no data"
    if metric == "is_rate":
        return f"Debt tax rate: {maps.cents_per_100(v)}"
    if metric == "residual":
        side = "more" if v > 0 else "less"
        return f"Spends {side} than expected for a district like it (score {v:+.1f})"
    if metric == "recapture":
        return (
            "Sends no money to the state"
            if v == 0
            else f"Sends {money(v)} per student to the state"
        )
    if metric == "growth":
        return f"Enrollment {'grew' if v >= 0 else 'shrank'} {abs(v):.0%} in 5 years"
    if metric == "new_campuses":
        return f"{v:.0f} new campuses since 2016-17"
    return f"{LAYERS[metric]['label']}: {fmt_map[LAYERS[metric]['fmt']](v)}"


tips = []
for r in df.itertuples():
    who = str(r.county).title() + (
        "" if pd.isna(r.enrollment) else f" · {r.enrollment:,.0f} students"
    )
    spend = f"Spends {money(r.op_per_student)} per student (Texas median {money(med_spend)})"
    prop = f"Taxable property: {fmt_map['money_k'](r.wealth_per_student)} per student"
    last = (
        metric_line(r)
        if view == "Single metric"
        else f"Typical household income: {fmt_map['money_k'](r.median_household_income)}"
    )
    tips.append(maps.tip(nice(r.district_name), who, spend, prop, last))
df = df.join(pd.DataFrame(tips, index=df.index))

geo = maps.features_with(
    data.geojson("tx_districts_simplified"),
    df,
    ["cdn", "district_name", "fill", *maps.TIP_KEYS] + (["elev"] if "elev" in df else []),
)
for f in geo["features"]:
    for k in maps.TIP_KEYS:  # deck.gl tooltips read top-level keys; keep one copy
        f[k] = f["properties"].pop(k)

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
        maps.deck(layers, view_state, "default", height=640),
        on_select="rerun",
        selection_mode="single-object",
        key=f"atlas_{view}_{metric}_{year}",
    )
    html_out(
        '<div class="ll-source">N ↑ · Map scale varies with latitude · Sources: Texas Education Agency (PEIMS), '
        "Texas Comptroller property values, U.S. Census Bureau, NCES, Texas Bond Review Board · Spending through "
        f"{sy(latest)}, debt through fiscal year {int(data.query('debt_state_year').fiscal_year.max())} · "
        "Basemap © CARTO, © OpenStreetMap</div>"
    )

with right:
    if view == "Bivariate":
        legend_bivariate()
        reading(
            "Two districts with the same color rank about the same on both wealth and spending."
        )
    elif view == "3D Wealth Relief":
        legend_diverging("Spending per student vs. Texas median", "below median", "above median")
        reading(
            "Taller districts have more property wealth per student. Teal districts spend less than the Texas "
            "median and clay districts spend more, so a tall teal district is wealthy but spends below the median. "
            + legend_note
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
            ("Taxable property per student", fmt_map["money_k"](r.wealth_per_student)),
            ("Typical household income", fmt_map["money_k"](r.median_household_income)),
            ("Sent to the state (recapture)", big_money(r.recapture_paid)),
        ]:
            st.markdown(f"**{label}**  \n`{val}`")
        st.page_link(
            "app_pages/district.py", label="Open full profile →", query_params={"district": sel}
        )
    else:
        st.caption("Click a district, or search above, to see its numbers here.")

    with st.expander("Take the tour" if not tour_on else "Tour", expanded=tour_on):
        if not tour_on:
            if st.button("Start the tour", type="primary"):
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
            if b1.button("← Back", disabled=i == 0):
                st.session_state.tour_step -= 1
                st.query_params["tour"] = str(st.session_state.tour_step)
                st.rerun()
            if b2.button("Next →", disabled=i == len(stops) - 1):
                st.session_state.tour_step += 1
                st.query_params["tour"] = str(st.session_state.tour_step)
                st.rerun()
            if b3.button("Exit tour"):
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
    label="Show the map as a table",
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
        '<div class="ll-finding"><div class="num">01</div>'
        f'<p class="ll-caption">Wealth explains {explained_words(last.elasticity_r2)} of the differences in '
        "district spending.</p><p>"
        + (
            f"In {sy(int(last.year))}, districts with 10% more property wealth per student spent <b>about the same</b> "
            f"per student: {more_less(per10(last.elasticity))}, give or take."
            if abs(per10(last.elasticity)) < 0.5
            else f"In {sy(int(last.year))}, districts with 10% more property wealth per student spent "
            f"<b>{more_less(per10(last.elasticity))}</b> per student, give or take."
        )
        + f" In {sy(int(first.year))}, they spent {more_less(per10(first.elasticity))}.</p></div>"
    )
    fig = go.Figure()
    fig.add_scatter(x=eq.year, y=eq.elasticity * 10, mode="lines+markers", line=dict(color=INK_2))
    fig.add_scatter(
        x=list(eq.year) + list(eq.year[::-1]),
        y=list(eq.elasticity_hi * 10) + list(eq.elasticity_lo[::-1] * 10),
        fill="toself",
        fillcolor="rgba(92,88,80,0.15)",
        line=dict(width=0),
        hoverinfo="skip",
    )
    fig.add_hline(y=0, line=dict(color=DIVERGING_7[0], width=1, dash="dot"))
    fig.update_layout(showlegend=False, yaxis_title="% change", margin=dict(t=10))
    charts.show(fig, height=180, key="f1")
    st.page_link("app_pages/wealth_spending.py", label="Explore →")
with f2:
    html_out(
        '<div class="ll-finding"><div class="num">02</div>'
        '<p class="ll-caption">The biggest over-spenders are tiny districts.</p><p>'
        + (
            f"<b>All {int(over.n)}</b> districts"
            if over.n_small == over.n
            else f"<b>{int(over.n_small)} of the {int(over.n)}</b> districts"
        )
        + " that spend the most above what we'd expect have fewer than 500 students."
        + f" The typical one has {over.median_enrollment:,.0f} students and spends "
        f"{money(over.median_actual)} per student, about {over.median_actual / over.median_predicted:.1f} times the "
        f"{money(over.median_predicted)} we'd expect from its wealth, students and location. Only "
        f"{pct(over.share_small_statewide, 0)} of Texas districts are that small.</p></div>"
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
    fig.update_xaxes(type="log", title="students (log scale)")
    fig.update_layout(yaxis_title="vs. expected", margin=dict(t=10))
    charts.show(fig, height=180, key="f2")
    st.page_link("app_pages/wealth_spending.py", label="Explore →")
with f3:
    html_out(
        '<div class="ll-finding"><div class="num">03</div>'
        f'<p class="ll-caption">{share_words(rec.paid_by_mineral_majority / rec.total_paid)} of recapture comes '
        "from mineral-rich districts.</p><p>"
        f"In {sy(latest)}, property-wealthy districts sent <b>{big_money(rec.total_paid)}</b> to the state. "
        f"{big_money(rec.paid_by_mineral_majority)} of it came from {int(rec.payers_mineral_majority)} districts "
        "where oil, gas and minerals make up most of the taxable property. And "
        f"{int(rec.payers_below_median_income)} of the {int(rec.payers)} paying districts have below-median "
        "household income, so a district can owe recapture even when its families aren't well off.</p></div>"
    )
    ry = data.query("recapture_by_year")
    fig = go.Figure(go.Bar(x=ry.year, y=ry.recapture_real / 1e9, marker_color=INK_2))
    fig.update_layout(yaxis_title=f"$ billions ({sy(latest)} dollars)", margin=dict(t=10))
    charts.show(fig, height=180, key="f3")
    st.page_link("app_pages/recapture.py", label="Explore →")
view_sql("findings", "finding_outliers", "finding_recapture", "recapture_by_year")
