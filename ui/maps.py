"""pydeck map helpers: classed colours, bivariate classes and the shared map frame.

Basemap: Carto "light" (Positron) via pydeck's built-in Carto provider, no token required.
"""

from __future__ import annotations

import copy
import math

import numpy as np
import pandas as pd
import pydeck as pdk

from ui.theme import BIVARIATE_3X3, DIVERGING_7, SEQUENTIAL_7

TX_VIEW = pdk.ViewState(latitude=31.1, longitude=-99.4, zoom=4.75, pitch=0, bearing=0)
CAPITOL = (-97.7404, 30.2747)  # Texas State Capitol, Austin (lon, lat)
NO_DATA = [217, 210, 195, 160]


def hex_rgb(h: str, a: int = 230) -> list[int]:
    h = h.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)] + [a]


def quantile_breaks(values: pd.Series, k: int = 7) -> list[float]:
    v = values.dropna()
    if v.empty:
        return []
    qs = np.unique(np.quantile(v, np.linspace(0, 1, k + 1)))
    return list(qs)


def classify(values: pd.Series, breaks: list[float]) -> pd.Series:
    if len(breaks) < 2:
        return pd.Series(np.nan, index=values.index)
    inner = breaks[1:-1]
    return pd.Series(np.searchsorted(inner, values, side="right"), index=values.index).where(
        values.notna()
    )


def class_colors(classes: pd.Series, palette: list[str]) -> pd.Series:
    n = len(palette)
    return classes.map(lambda c: NO_DATA if pd.isna(c) else hex_rgb(palette[min(int(c), n - 1)]))


def tercile(values: pd.Series) -> pd.Series:
    return pd.qcut(values.rank(method="first"), 3, labels=[1, 2, 3]).astype("float")


def bivariate_colors(wealth: pd.Series, spend: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    w, s = tercile(wealth), tercile(spend)
    col = [
        NO_DATA if (pd.isna(a) or pd.isna(b)) else hex_rgb(BIVARIATE_3X3[(int(a), int(b))])
        for a, b in zip(w, s, strict=True)
    ]
    return pd.Series(col, index=wealth.index), w, s


def diverging_colors(values: pd.Series, center: float) -> pd.Series:
    """7 classes around `center` using symmetric quantiles of |value - center|."""
    d = values - center
    m = d.abs().quantile(0.95) or 1.0
    edges = np.array([-np.inf, -0.6, -0.3, -0.1, 0.1, 0.3, 0.6, np.inf]) * m
    cls = pd.Series(np.digitize(d, edges[1:-1]), index=values.index).where(values.notna())
    return class_colors(cls, DIVERGING_7)


def features_with(geo: dict, df: pd.DataFrame, cols: list[str], key: str = "geoid") -> dict:
    """Copy the GeoJSON and attach df columns (looked up by GEOID) to feature properties."""
    lookup = df.set_index(key)[cols].to_dict("index")
    out = copy.copy(geo)
    feats = []
    for f in geo["features"]:
        rec = lookup.get(f["properties"]["geoid"])
        if rec is None:
            continue
        feats.append(
            {"type": "Feature", "geometry": f["geometry"], "properties": {**f["properties"], **rec}}
        )
    out["features"] = feats
    return out


def fmt_money(v) -> str:
    return "n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f"${v:,.0f}"


def overlay_layer(geo: dict, layer_id: str, color=(27, 26, 23, 110), width=1.2) -> pdk.Layer:
    return pdk.Layer(
        "GeoJsonLayer",
        geo,
        id=layer_id,
        stroked=True,
        filled=False,
        pickable=False,
        get_line_color=list(color),
        line_width_min_pixels=width,
    )


def deck(layers, view=TX_VIEW, tooltip_html: str | None = None, height: int = 620) -> pdk.Deck:
    tooltip = None
    if tooltip_html:
        tooltip = {
            "html": tooltip_html,
            "style": {
                "backgroundColor": "#FBF8F2",
                "color": "#1B1A17",
                "border": "1px solid #D9D2C3",
                "fontFamily": "JetBrains Mono, monospace",
                "fontSize": "13px",
                "padding": "8px 10px",
                "borderRadius": "4px",
            },
        }
    return pdk.Deck(
        layers=layers,
        initial_view_state=view,
        map_provider="carto",
        map_style="light",
        tooltip=tooltip,
        height=height,
    )


SEQ = SEQUENTIAL_7


def flat_arc(src, dst, bend: float = 0.18, n: int = 24) -> list[list[float]]:
    """A gently curved 2D path (quadratic Bezier) from src to dst, both (lon, lat)."""
    (x0, y0), (x1, y1) = src, dst
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy * bend, my + dx * bend  # control point offset perpendicular to the chord
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(
            [
                (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t**2 * x1,
                (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t**2 * y1,
            ]
        )
    return pts
