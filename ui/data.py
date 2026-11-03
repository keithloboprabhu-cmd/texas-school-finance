"""Read-only access to the committed marts.

At startup the app reads only `data/marts/*.parquet` and the simplified GeoJSON.
It never makes network calls.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
MARTS = ROOT / "data" / "marts"


def mart_path(name: str) -> Path:
    return MARTS / f"{name}.parquet"


def mart_exists(name: str) -> bool:
    return mart_path(name).exists()


def available_marts() -> list[str]:
    return sorted(p.stem for p in MARTS.glob("*.parquet"))


@st.cache_data(show_spinner=False)
def load_mart(name: str) -> pd.DataFrame:
    return pd.read_parquet(mart_path(name))


@st.cache_resource(show_spinner=False)
def warehouse() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with one view per committed mart, locked down for read-only use."""
    from ui.sql_guard import harden_connection

    con = duckdb.connect(":memory:")
    for name in available_marts():
        path = mart_path(name).as_posix().replace("'", "''")
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM read_parquet('{path}')")
    harden_connection(con)
    return con
