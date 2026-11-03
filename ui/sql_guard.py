"""Safety layer for the SQL Lab.

Rules (Section 7.4 of the build spec):
  * read-only in-memory DuckDB over the marts only
  * exactly one statement, and it must be a SELECT (a WITH ... SELECT counts)
  * at most MAX_ROWS rows returned
  * QUERY_TIMEOUT_S seconds, then the query is interrupted
  * no file-system or network access (DuckDB `enable_external_access = false`, config locked)

Statement type is checked with DuckDB's own parser (`extract_statements`), not a regex.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass

import duckdb
import pandas as pd

MAX_ROWS = 10_000
QUERY_TIMEOUT_S = 3.0
MAX_QUERY_CHARS = 20_000

_LEADING_COMMENTS = re.compile(r"^\s*(?:(?:--[^\n]*\n?)|(?:/\*.*?\*/)|\s)*", re.DOTALL)


class QueryRejected(ValueError):
    """The query is not allowed in the SQL Lab. The message is shown to the user."""


@dataclass
class QueryResult:
    frame: pd.DataFrame
    truncated: bool
    elapsed_s: float


def harden_connection(con: duckdb.DuckDBPyConnection) -> None:
    """Turn off file/network access and extension loading, then lock the configuration."""
    con.execute("SET enable_external_access = false")
    con.execute("SET autoinstall_known_extensions = false")
    con.execute("SET autoload_known_extensions = false")
    con.execute("SET lock_configuration = true")


def validate(sql: str) -> str:
    """Return the single SELECT statement (without trailing semicolon) or raise QueryRejected."""
    if not sql or not sql.strip():
        raise QueryRejected("Enter a query.")
    if len(sql) > MAX_QUERY_CHARS:
        raise QueryRejected(f"Query is longer than {MAX_QUERY_CHARS:,} characters.")

    body = _LEADING_COMMENTS.sub("", sql)
    first_word = (re.match(r"[A-Za-z]+", body) or [""])[0].upper()
    if first_word not in {"SELECT", "WITH"}:
        raise QueryRejected("Only SELECT queries (optionally starting with WITH) are allowed.")

    try:
        statements = duckdb.extract_statements(sql)
    except duckdb.Error as exc:
        raise QueryRejected(f"Could not parse query: {exc}") from exc
    if len(statements) != 1:
        raise QueryRejected("Run one statement at a time.")
    stmt = statements[0]
    if stmt.type != duckdb.StatementType.SELECT:
        raise QueryRejected("Only SELECT queries are allowed.")
    return stmt.query.strip().rstrip(";")


def run_query(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    max_rows: int = MAX_ROWS,
    timeout_s: float = QUERY_TIMEOUT_S,
) -> QueryResult:
    """Validate and run a query with a row cap and a timeout."""
    query = validate(sql)
    wrapped = f"SELECT * FROM (\n{query}\n) AS sql_lab_q LIMIT {int(max_rows) + 1}"

    cur = con.cursor()
    timer = threading.Timer(timeout_s, cur.interrupt)
    start = time.perf_counter()
    timer.start()
    try:
        frame = cur.execute(wrapped).df()
    except duckdb.InterruptException as exc:
        raise QueryRejected(f"Query stopped after {timeout_s:g} seconds.") from exc
    except duckdb.Error as exc:
        if time.perf_counter() - start >= timeout_s:
            raise QueryRejected(f"Query stopped after {timeout_s:g} seconds.") from exc
        raise QueryRejected(str(exc).split("\n")[0]) from exc
    finally:
        timer.cancel()
        cur.close()
    elapsed = time.perf_counter() - start

    truncated = len(frame) > max_rows
    return QueryResult(frame.head(max_rows), truncated, elapsed)
