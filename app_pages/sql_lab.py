"""SQL Lab: read-only DuckDB over the committed marts, with saved queries."""

import time
from pathlib import Path

import streamlit as st

from ui import data
from ui.components import page_header
from ui.sql_guard import MAX_ROWS, QUERY_TIMEOUT_S, QueryRejected, run_query

SAVED = Path(__file__).resolve().parent.parent / "sql" / "saved"

page_header(
    "SQL Lab",
    "Query the warehouse",
    "The same DuckDB marts that power every chart. Read-only: one SELECT at a time, "
    f"{MAX_ROWS:,} rows, {QUERY_TIMEOUT_S:g} seconds.",
)

tables = data.available_marts()
if not tables:
    st.html(
        '<div class="ll-notice"><strong>No marts built yet.</strong> '
        "Run <code>make data</code> to build the warehouse; tables will appear here.</div>"
    )
    st.stop()

saved = {}
for p in sorted(SAVED.glob("*.sql")):
    text = p.read_text(encoding="utf-8")
    saved[text.splitlines()[0].lstrip("- ").strip()] = text  # first comment line = description
left, right = st.columns([3, 1], gap="large")
with right:
    st.subheader("Schema", anchor=False)
    con = data.warehouse()
    for t in tables:
        with st.expander(t):
            cols = con.execute(f"DESCRIBE {t}").df()[["column_name", "column_type"]]
            st.dataframe(cols, hide_index=True, width="stretch")
with left:
    choice = st.selectbox("Saved queries", ["(write your own)", *saved])
    default = saved.get(choice, f"SELECT *\nFROM {tables[0]}\nLIMIT 20")
    sql = st.text_area("SQL", value=default, height=220, key=f"sql_{choice}")
    if st.button("Run", type="primary"):
        try:
            t0 = time.perf_counter()
            res = run_query(data.warehouse(), sql)
            note = " (truncated)" if res.truncated else ""
            st.caption(f"{len(res.frame):,} rows{note} · {res.elapsed_s * 1000:,.0f} ms")
            st.dataframe(res.frame, hide_index=True, width="stretch")
        except QueryRejected as exc:
            st.error(str(exc))
