"""Every SQL file behind the app runs against the committed marts (catches broken chart queries in CI)."""

import re
from pathlib import Path

import duckdb
import pytest
from conftest import MARTS, needs

APP_SQL = Path(__file__).resolve().parent.parent / "sql" / "app"
SAVED_SQL = Path(__file__).resolve().parent.parent / "sql" / "saved"
PARAMS = {"year": 2025, "cdn": "227909"}  # Eanes ISD (see mart_districts)


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    for p in MARTS.glob("*.parquet"):
        c.execute(f"CREATE TABLE {p.stem} AS SELECT * FROM read_parquet('{p.as_posix()}')")
    yield c
    c.close()


@needs(MARTS / "mart_district_year.parquet")
@pytest.mark.parametrize(
    "path", sorted(APP_SQL.glob("*.sql")) + sorted(SAVED_SQL.glob("*.sql")), ids=lambda p: p.stem
)
def test_query_runs(con, path):
    sql = path.read_text()
    used = set(re.findall(r"\$(\w+)", sql))
    df = con.execute(sql, {k: v for k, v in PARAMS.items() if k in used}).df()
    assert len(df.columns) > 0
