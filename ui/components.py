"""Small, reusable page elements styled to the Modern Almanac tokens."""

from __future__ import annotations

import html

import streamlit as st

from ui import data


def page_header(kicker: str, title: str, subtitle: str | None = None) -> None:
    st.html(f'<div class="ll-kicker">{html.escape(kicker)}</div>')
    st.title(title, anchor=False)
    if subtitle:
        st.html(f'<p class="ll-subtitle">{html.escape(subtitle)}</p>')


def rule() -> None:
    st.html('<hr class="ll-rule">')


def metric(label: str, value: str) -> None:
    st.html(
        f'<div class="ll-metric"><div class="value">{html.escape(value)}</div>'
        f'<div class="label">{html.escape(label)}</div></div>'
    )


def require_marts(*names: str) -> bool:
    """Show an honest notice and return False if any required mart has not been built yet.

    The app never shows placeholder or sample numbers: until the pipeline has produced
    the marts, pages say so instead.
    """
    missing = [n for n in names if not data.mart_exists(n)]
    if not missing:
        return True
    items = "".join(f"<li><code>data/marts/{html.escape(n)}.parquet</code></li>" for n in missing)
    st.html(
        '<div class="ll-notice"><strong>Data not built yet.</strong> '
        "This page needs the following marts, which are produced by <code>make data</code>:"
        f"<ul>{items}</ul>No placeholder numbers are shown in the meantime.</div>"
    )
    return False
