"""Read-only access to the committed marts and map layers.

At startup the app reads only `data/marts/*.parquet` and `data/geo/*.geojson`, builds an in-memory
DuckDB from them and never makes network calls. Chart data comes from SQL files in `sql/app/`
(shown verbatim by every chart's "View SQL" expander).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent.parent
MARTS = ROOT / "data" / "marts"
GEO = ROOT / "data" / "geo"
APP_SQL = ROOT / "sql" / "app"
CONFIG = ROOT / "config"


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
    """In-memory DuckDB with one table per committed mart, locked down for read-only use."""
    from ui.sql_guard import harden_connection

    con = duckdb.connect(":memory:")
    for name in available_marts():
        path = mart_path(name).as_posix().replace("'", "''")
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM read_parquet('{path}')")
    harden_connection(con)
    return con


@st.cache_data(show_spinner=False)
def sql_text(name: str) -> str:
    return (APP_SQL / f"{name}.sql").read_text(encoding="utf-8")


@st.cache_data(show_spinner=False)
def query(name: str, **params) -> pd.DataFrame:
    """Run sql/app/<name>.sql with named parameters ($year, $cdn, ...)."""
    sql = sql_text(name)
    used = set(re.findall(r"\$(\w+)", sql))
    cur = warehouse().cursor()
    try:
        return cur.execute(sql, {k: v for k, v in params.items() if k in used}).df()
    finally:
        cur.close()


@st.cache_data(show_spinner=False)
def geojson(name: str) -> dict:
    return json.loads((GEO / f"{name}.geojson").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def config(name: str) -> dict:
    return yaml.safe_load((CONFIG / f"{name}.yaml").read_text(encoding="utf-8"))


def latest_year() -> int:
    return int(query("meta_years").year.max())
