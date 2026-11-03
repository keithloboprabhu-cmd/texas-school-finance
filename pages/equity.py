"""Equity Over Time: statewide spending equity, 2009 to the latest year, in real dollars."""

from ui.components import page_header, require_marts

page_header(
    "05 · Over time",
    "Equity Over Time",
    "How unequal is per-student spending across Texas, and how has that changed?",
)
require_marts("mart_equity_state_year")
