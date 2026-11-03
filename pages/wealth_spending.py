"""Wealth & Spending: how per-student spending tracks property wealth, and the outliers."""

from ui.components import page_header, require_marts

page_header(
    "01 · The core question",
    "Wealth & Spending",
    "Does a district's property wealth predict how much it spends per student?",
)
require_marts("mart_district_year", "mart_outliers_latest")
