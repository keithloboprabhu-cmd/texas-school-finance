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
    st.Page("app_pages/atlas.py", title="Atlas", url_path="atlas", default=True),
    st.Page("app_pages/wealth_spending.py", title="Wealth & Spending", url_path="wealth-spending"),
    st.Page("app_pages/recapture.py", title="Recapture", url_path="recapture"),
    st.Page("app_pages/bonds_debt.py", title="Bonds & Debt", url_path="bonds-debt"),
    st.Page("app_pages/growth_construction.py", title="Growth & Construction", url_path="growth"),
    st.Page("app_pages/equity.py", title="Equity Over Time", url_path="equity"),
    st.Page("app_pages/district.py", title="District Profile", url_path="district"),
    st.Page("app_pages/sql_lab.py", title="SQL Lab", url_path="sql-lab"),
    st.Page("app_pages/methodology.py", title="Methodology & Data", url_path="methodology"),
]

st.navigation(PAGES, position="top").run()
