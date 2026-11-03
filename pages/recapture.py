"""Recapture: districts that send excess local revenue to the state."""

from ui.components import page_header, require_marts

page_header(
    "02 · Robin Hood",
    "Recapture",
    "Which districts send local property-tax revenue to the state, and how much.",
)
require_marts("mart_recapture", "mart_money_cycle_state_year")
