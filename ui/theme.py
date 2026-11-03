"""Design tokens and CSS injection for the "Modern Almanac" look.

The same token values live in `.streamlit/config.toml` (Streamlit theme) and
`assets/app.css` (custom CSS). Data palettes are defined here so charts and maps share them.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent

PAPER = "#F5F1E8"
CARD = "#FBF8F2"
INK = "#1B1A17"
INK_2 = "#5C5850"
RULE = "#D9D2C3"
LAND = "#ECE6D9"
CLAY = "#A8432A"  # accent for selection/focus/links only, never data

# 7-class sequential ramp (viridis family, perceptually uniform, colorblind-safe).
SEQUENTIAL_7 = ["#440154", "#443983", "#31688E", "#21918C", "#35B779", "#90D743", "#FDE725"]

# Diverging teal <-> clay centered on a paper-coloured midpoint (residuals, vs-median).
DIVERGING_7 = ["#1F6F6B", "#5B9A93", "#A9C7BF", "#EFE9DD", "#D9A88F", "#C0705A", "#8F3A24"]

# Bivariate 3x3 (wealth x spending), after Joshua Stevens' blue-pink scheme.
# Key is (wealth_class, spending_class), each 1 (low) .. 3 (high).
# Still to do before release: deuteranopia simulation and grayscale check (Methodology page).
BIVARIATE_3X3 = {
    (1, 1): "#E8E8E8",
    (2, 1): "#E4ACAC",
    (3, 1): "#C85A5A",
    (1, 2): "#B0D5DF",
    (2, 2): "#AD9EA5",
    (3, 2): "#985356",
    (1, 3): "#64ACBE",
    (2, 3): "#627F8C",
    (3, 3): "#574249",
}


@cache
def _css() -> str:
    return (ROOT / "assets" / "app.css").read_text(encoding="utf-8")


def apply_theme() -> None:
    """Inject the custom CSS. Call once per page run (from app.py)."""
    st.markdown(f"<style>{_css()}</style>", unsafe_allow_html=True)


def html(markup: str) -> None:
    """Render raw HTML through Streamlit's Markdown element.

    Used instead of st.html: on Streamlit Community Cloud the separate Html front-end module failed to
    load in some browsers ("Failed to fetch dynamically imported module .../Html.*.js"), while Markdown
    is always loaded. Dollar signs are escaped so Markdown does not render them as LaTeX, and newlines
    are collapsed so indented HTML is not mistaken for a Markdown code block.
    """
    safe = markup.replace("$", "&#36;").replace("\n", " ")
    st.markdown(safe, unsafe_allow_html=True)


@cache
def _star_svg() -> str:
    return (ROOT / "assets" / "lone-star.svg").read_text(encoding="utf-8")


def brand_bar() -> None:
    """Site title with the lone-star mark, shown above every page."""
    html(
        '<div class="ll-brand">'
        f'<span class="ll-brand-star" aria-hidden="true">{_star_svg()}</span>'
        '<span class="ll-brand-name">Lone Star Education Ledger</span>'
        '<span class="ll-brand-sub">Texas School Finance Atlas</span>'
        "</div>"
    )
