"""Growth & Construction: enrollment growth, new campuses and capital spending."""

from ui.components import page_header, require_marts

page_header(
    "04 · Building", "Growth & Construction", "Where Texas is growing, and where it is building."
)
require_marts("mart_campuses", "mart_growth_capital")
