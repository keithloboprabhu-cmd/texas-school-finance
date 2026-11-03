"""Small, reusable page elements styled to the Modern Almanac tokens."""

from __future__ import annotations

import html
import re

import pandas as pd
import streamlit as st

from ui import data
from ui.theme import BIVARIATE_3X3, DIVERGING_7, SEQUENTIAL_7
from ui.theme import html as html_out


def page_header(kicker: str, title: str, subtitle: str | None = None) -> None:
    html_out(f'<div class="ll-kicker">{html.escape(kicker)}</div>')
    st.title(title, anchor=False)
    if subtitle:
        html_out(f'<p class="ll-subtitle">{html.escape(subtitle)}</p>')


def rule() -> None:
    html_out('<hr class="ll-rule">')


def metric(label: str, value: str, note: str | None = None) -> None:
    n = f'<div class="note">{html.escape(note)}</div>' if note else ""
    html_out(
        f'<div class="ll-metric"><div class="value">{html.escape(value)}</div>'
        f'<div class="label">{html.escape(label)}</div>{n}</div>'
    )


def reading(text: str) -> None:
    """One-line 'how to read this'."""
    html_out(f'<p class="ll-reading">{html.escape(text)}</p>')


def notice(title: str, body: str) -> None:
    html_out(f'<div class="ll-notice"><strong>{html.escape(title)}</strong> {body}</div>')


def term(key: str, text: str | None = None) -> str:
    """Inline glossary term with a dotted underline and hover definition (returns HTML)."""
    g = data.config("glossary").get(key, {})
    return (
        f'<abbr class="ll-term" title="{html.escape(g.get("definition", ""))}">'
        f"{html.escape(text or g.get('label', key))}</abbr>"
    )


def glossary_help(key: str) -> str:
    return data.config("glossary").get(key, {}).get("definition", "")


def view_sql(*names: str) -> None:
    with st.expander("View SQL"):
        for n in names:
            st.code(data.sql_text(n), language="sql")


def view_table(df: pd.DataFrame, key: str, label: str = "View as table", **kw) -> None:
    if st.toggle(label, key=f"tbl_{key}"):
        st.dataframe(df, hide_index=True, width="stretch", **kw)


def legend_quantile(title: str, breaks: list[float], fmt, palette=SEQUENTIAL_7) -> None:
    if len(breaks) < 2:
        return
    items = []
    for i in range(len(breaks) - 1):
        col = palette[min(i, len(palette) - 1)]
        items.append(
            f'<div class="ll-leg-item"><span class="sw" style="background:{col}"></span>'
            f"{html.escape(fmt(breaks[i]))} to {html.escape(fmt(breaks[i + 1]))}</div>"
        )
    html_out(
        f'<div class="ll-legend"><div class="ll-leg-title">{html.escape(title)} '
        f'<span class="ll-caption">(7 quantile classes)</span></div>{"".join(items)}</div>'
    )


def legend_diverging(title: str, low: str, high: str) -> None:
    sw = "".join(f'<span class="sw" style="background:{c}"></span>' for c in DIVERGING_7)
    html_out(
        f'<div class="ll-legend"><div class="ll-leg-title">{html.escape(title)}</div>'
        f'<div class="ll-div">{sw}</div><div class="ll-div-labels"><span>{html.escape(low)}</span>'
        f"<span>{html.escape(high)}</span></div></div>"
    )


def legend_bivariate() -> None:
    cells = []
    for s in (3, 2, 1):
        for w in (1, 2, 3):
            cells.append(f'<span style="background:{BIVARIATE_3X3[(w, s)]}"></span>')
    html_out(
        '<div class="ll-legend ll-bivar"><div class="grid">' + "".join(cells) + "</div>"
        '<div class="axes"><div>more spending per student &uarr;</div><div>more property wealth per student &rarr;</div>'
        '<div class="ll-caption">Each axis split into thirds of districts. Dark purple: wealthy and high-spending. '
        "Pink: wealthy, lower spending. Blue: less wealthy, higher spending.</div></div></div>"
    )


def require_marts(*names: str) -> bool:
    """Show an honest notice and return False if any required mart has not been built yet."""
    missing = [n for n in names if not data.mart_exists(n)]
    if not missing:
        return True
    items = "".join(f"<li><code>data/marts/{html.escape(n)}.parquet</code></li>" for n in missing)
    html_out(
        '<div class="ll-notice"><strong>Data not built yet.</strong> This page needs marts produced by '
        f"<code>make data</code>:<ul>{items}</ul>No placeholder numbers are shown in the meantime.</div>"
    )
    return False


def sy(year: int) -> str:
    """School-year label: 2025 -> '2024-25'."""
    return f"{year - 1}-{str(year)[2:]}"


def money(v, digits: int = 0) -> str:
    return "n/a" if v is None or pd.isna(v) else f"${v:,.{digits}f}"


def pct(v, digits: int = 1) -> str:
    return "n/a" if v is None or pd.isna(v) else f"{v * 100:.{digits}f}%"


def big_money(v) -> str:
    if v is None or pd.isna(v):
        return "n/a"
    for div, suf in [(1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if abs(v) >= div:
            return f"${v / div:,.1f}{suf}"
    return f"${v:,.0f}"


def nice(name) -> str:
    """Title-case a TEA district name but keep ISD/CISD/CSD and similar abbreviations upper-case."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = str(name).title()
    return re.sub(r"\b(Isd|Cisd|Csd|Msd|Ccsd|Ftw|Ii|Iii)\b", lambda m: m.group(1).upper(), s)


def md_money(text: str) -> str:
    """Escape dollar signs so Streamlit markdown does not render them as LaTeX."""
    return text.replace("$", "\\$")
