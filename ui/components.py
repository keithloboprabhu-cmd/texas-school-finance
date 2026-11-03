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
    with st.expander("Show the SQL"):
        for n in names:
            st.code(data.sql_text(n), language="sql")


def view_table(df: pd.DataFrame, key: str, label: str = "Show as a table", **kw) -> None:
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
        f'<span class="ll-caption">(each color covers about 1 in 7 districts)</span></div>{"".join(items)}</div>'
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
        '<div class="ll-caption">Districts are split into thirds on each measure. Dark purple: high wealth and high '
        "spending. Pink: high wealth, lower spending. Blue: lower wealth, higher spending.</div></div></div>"
    )


def require_marts(*names: str) -> bool:
    """Show an honest notice and return False if any required mart has not been built yet."""
    missing = [n for n in names if not data.mart_exists(n)]
    if not missing:
        return True
    items = "".join(f"<li><code>data/marts/{html.escape(n)}.parquet</code></li>" for n in missing)
    html_out(
        '<div class="ll-notice"><strong>The data for this page isn\'t built yet.</strong> Run '
        f"<code>make data</code> to create these files:<ul>{items}</ul>Until then, this page shows no numbers.</div>"
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


# ---------------------------------------------------------------- plain-language number phrasing
def per10(b: float) -> float:
    """Elasticity -> % change in spending for 10% more wealth (b x 10)."""
    return b * 10


def pct_words(p: float, digits: int = 2) -> str:
    """'0.67%' (no sign; direction is said in words)."""
    return f"{abs(p):.{digits}f}%"


def more_less(p: float, noun: str = "", digits: int = 2) -> str:
    """'0.67% more' / '0.03% less'."""
    return f"{pct_words(p, digits)} {'more' if p >= 0 else 'less'}{(' ' + noun) if noun else ''}"


def range_words(lo: float, hi: float, digits: int = 2) -> str:
    """'between 0.37% less and 0.30% more' / 'between 0.43% and 0.92% more'."""
    if lo >= 0:
        return f"between {abs(lo):.{digits}f}% and {abs(hi):.{digits}f}% more"
    if hi <= 0:
        return f"between {abs(hi):.{digits}f}% and {abs(lo):.{digits}f}% less"
    return f"between {abs(lo):.{digits}f}% less and {abs(hi):.{digits}f}% more"


def zero_sentence(lo: float, hi: float, what: str = "wealth") -> str:
    """Say what zero means and whether it is inside the likely range."""
    if lo <= 0 <= hi:
        return (
            f"If {what} made no difference at all, this number would be exactly zero. "
            "Given the uncertainty, zero is well within range."
        )
    side = "more" if lo > 0 else "less"
    return (
        f"Even allowing for uncertainty, the number stays above zero, so districts with more {what} "
        f"really do spend {side}."
        if side == "more"
        else f"Even allowing for uncertainty, the number stays below zero, so districts with more {what} "
        "really do spend less."
    )


def explained_words(r2: float) -> str:
    """Plain reading of R-squared."""
    if r2 < 0.05:
        return "almost none"
    if r2 < 0.2:
        return "a little"
    if r2 < 0.5:
        return "some"
    return "much"


def growth_effect_text(
    slope: float,
    lo: float,
    hi: float,
    lead_more: str,
    lead_less: str,
    verb_more: str,
    verb_less: str,
    n: int,
    extra: str = "",
) -> tuple[str, str]:
    """Lead line and sentence for 'X per student vs. 5-year growth' fits on a log scale.
    slope/lo/hi are per 1.0 (100 points) of growth; we describe 10 points. verb_* contain '{pct}'."""
    import math

    eff, elo, ehi = (math.exp(v * 0.1) - 1 for v in (slope, lo, hi))
    up = eff >= 0
    rng = (
        f"between {abs(elo):.0%} and {abs(ehi):.0%} {'more' if up else 'less'}"
        if (elo >= 0) == (ehi >= 0)
        else f"between {abs(elo):.0%} less and {abs(ehi):.0%} more"
    )
    verb = (verb_more if up else verb_less).format(pct=f"{abs(eff):.0%}")
    body = (
        f"A district whose enrollment grew 10 percentage points faster over five years {verb}, give or take "
        f"(likely range: {rng}). Based on {n:,} districts{extra}; larger districts count for more. This shows a "
        "pattern, not proof that one causes the other."
    )
    return (lead_more if up else lead_less), body


def share_words(x: float) -> str:
    """0.33 -> 'About a third'; falls back to a percentage."""
    for lo, hi, w in [
        (0.23, 0.27, "About a quarter"),
        (0.30, 0.36, "About a third"),
        (0.47, 0.53, "About half"),
        (0.63, 0.70, "About two-thirds"),
        (0.72, 0.78, "About three-quarters"),
    ]:
        if lo <= x <= hi:
            return w
    return f"{x:.0%}"


def change_words(x: float, digits: int = 1) -> str:
    """-0.068 -> 'fell 6.8%'; 0.12 -> 'grew 12.0%'."""
    if x is None or x != x:
        return "has no comparable figure"
    return f"{'grew' if x >= 0 else 'fell'} {abs(x) * 100:.{digits}f}%"


FUNCTION_LABELS = {
    "instruction": "Teaching",
    "instructional support": "Teaching support and libraries",
    "school leadership": "Principals and school leadership",
    "student support": "Counseling, health and social work",
    "transportation": "Buses",
    "food service": "School meals",
    "extracurricular": "Sports and activities",
    "general administration": "Central administration",
    "plant maintenance security": "Building upkeep and security",
    "data processing": "Technology",
    "community services": "Community services",
}
