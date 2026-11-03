"""Bonds & Debt: bond elections, outstanding debt, the maturity wall and I&S rates."""

from ui.components import page_header, require_marts

page_header(
    "03 · Borrowing",
    "Bonds & Debt",
    "What districts ask voters to borrow, what they owe, and when it comes due.",
)
require_marts("mart_bond_elections", "mart_debt_district", "mart_maturity_wall", "mart_tax_rates")
