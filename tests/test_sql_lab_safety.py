import duckdb
import pytest

from ui.sql_guard import QueryRejected, harden_connection, run_query, validate


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    c.execute("CREATE TABLE mart_demo AS SELECT range AS i FROM range(50000)")
    harden_connection(c)
    yield c
    c.close()


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select i from mart_demo where i < 5",
        "WITH t AS (SELECT 1 AS x) SELECT x FROM t",
        "-- a comment\nSELECT 1;",
        "/* block */ SELECT 1",
    ],
)
def test_allows_selects(sql):
    validate(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "DROP TABLE mart_demo",
        "DELETE FROM mart_demo",
        "INSERT INTO mart_demo VALUES (1)",
        "UPDATE mart_demo SET i = 0",
        "CREATE TABLE x AS SELECT 1",
        "ATTACH 'other.db'",
        "COPY mart_demo TO 'out.csv'",
        "PRAGMA database_list",
        "SET enable_external_access = true",
        "INSTALL httpfs",
        "LOAD httpfs",
        "SELECT 1; DROP TABLE mart_demo",
        "SELECT 1; SELECT 2",
        "EXPORT DATABASE 'x'",
        "FROM mart_demo",  # DuckDB FROM-first syntax: spec allows SELECT/WITH only
        "WITH t AS (SELECT 1) DELETE FROM mart_demo",
    ],
)
def test_rejects_non_select(sql):
    with pytest.raises(QueryRejected):
        validate(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM read_csv_auto('/etc/passwd')",
        "SELECT * FROM read_text('/etc/hostname')",
        "SELECT * FROM glob('/*')",
        "SELECT * FROM read_parquet('https://example.com/x.parquet')",
    ],
)
def test_blocks_file_and_network_access(con, sql):
    with pytest.raises(QueryRejected):
        run_query(con, sql)


def test_config_is_locked(con):
    with pytest.raises(duckdb.Error):
        con.execute("SET enable_external_access = true")


def test_row_limit(con):
    res = run_query(con, "SELECT i FROM mart_demo", max_rows=10_000)
    assert len(res.frame) == 10_000
    assert res.truncated
    res = run_query(con, "SELECT i FROM mart_demo LIMIT 5")
    assert len(res.frame) == 5
    assert not res.truncated


def test_timeout(con):
    slow = "SELECT count(*) FROM range(100000000) a, range(100000000) b"
    with pytest.raises(QueryRejected, match="stopped"):
        run_query(con, slow, timeout_s=0.5)


def test_writes_impossible_even_inside_select(con):
    with pytest.raises(QueryRejected):
        run_query(con, "SELECT * FROM (DELETE FROM mart_demo RETURNING *)")
    assert con.execute("SELECT count(*) FROM mart_demo").fetchone()[0] == 50000
