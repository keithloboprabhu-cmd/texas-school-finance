"""Lone Star Ledger: Texas School Finance Atlas. Streamlit entry point."""

import streamlit as st

from ui.theme import apply_theme

st.set_page_config(
    page_title="Lone Star Ledger · Texas School Finance Atlas",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()

PAGES = [
    st.Page("pages/atlas.py", title="Atlas", url_path="atlas", default=True),
    st.Page("pages/wealth_spending.py", title="Wealth & Spending", url_path="wealth-spending"),
    st.Page("pages/recapture.py", title="Recapture", url_path="recapture"),
    st.Page("pages/bonds_debt.py", title="Bonds & Debt", url_path="bonds-debt"),
    st.Page("pages/growth_construction.py", title="Growth & Construction", url_path="growth"),
    st.Page("pages/equity.py", title="Equity Over Time", url_path="equity"),
    st.Page("pages/district.py", title="District Profile", url_path="district"),
    st.Page("pages/sql_lab.py", title="SQL Lab", url_path="sql-lab"),
    st.Page("pages/methodology.py", title="Methodology & Data", url_path="methodology"),
]

st.navigation(PAGES, position="top").run()
