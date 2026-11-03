"""Plotly styling for the Modern Almanac look: paper background, hairline grid, mono ticks."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from ui.theme import CLAY, INK, INK_2, PAPER, RULE

FONT = "Inter Tight, system-ui, sans-serif"
MONO = "JetBrains Mono, ui-monospace, monospace"

pio.templates["almanac"] = go.layout.Template(
    layout=dict(
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font=dict(family=FONT, color=INK, size=14),
        title=dict(font=dict(family="Fraunces, Georgia, serif", size=20), x=0, xanchor="left"),
        xaxis=dict(
            gridcolor=RULE,
            linecolor=INK_2,
            zeroline=False,
            tickfont=dict(family=MONO, size=13),
            title=dict(font=dict(size=14, color=INK_2)),
        ),
        yaxis=dict(
            gridcolor=RULE,
            linecolor=INK_2,
            zeroline=False,
            tickfont=dict(family=MONO, size=13),
            title=dict(font=dict(size=14, color=INK_2)),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=13)),
        hoverlabel=dict(
            bgcolor="#FBF8F2", bordercolor=RULE, font=dict(family=MONO, size=13, color=INK)
        ),
        margin=dict(l=8, r=8, t=40, b=8),
        colorway=["#31688E", "#A8432A", "#35B779", "#5C5850", "#90D743", "#443983"],
    )
)
pio.templates.default = "almanac"

CONFIG = {"displayModeBar": False, "responsive": True}
ACCENT = CLAY


def show(fig: go.Figure, height: int = 420, key: str | None = None) -> None:
    import streamlit as st

    fig.update_layout(height=height)
    st.plotly_chart(fig, config=CONFIG, key=key, width="stretch")
