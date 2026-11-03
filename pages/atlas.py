"""Atlas (home): the Texas map, layer switcher, overlays, findings strip and guided tour."""

from ui.components import page_header, require_marts

page_header(
    "Lone Star Ledger · Texas School Finance Atlas",
    "Where the money goes in Texas schools",
    "Property wealth, spending, recapture, debt and growth for every Texas school district.",
)
require_marts("mart_district_year")
