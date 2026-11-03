"""Run the whole pipeline idempotently and print a data-quality report.

  download (pipeline/ingest) -> clean (pandas) -> Parquet (data/processed)
  -> DuckDB SQL (sql/ref, staging, core, marts) -> analysis (Python) -> data/marts/*.parquet

Usage: python -m pipeline.build [--refresh]   (or `make data`)
  --refresh  re-run every ingest step even when its processed output exists
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "sql"
PROCESSED = ROOT / "data" / "processed"
MARTS = ROOT / "data" / "marts"
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"

# ingest module -> processed outputs it produces
INGEST = {
    "pipeline.ingest.tea_peims": ["peims_summarized.parquet", "peims_actuals"],
    "pipeline.ingest.tea_wealth": [
        "property_values.parquet",
        "property_mix.parquet",
        "tax_rates.parquet",
    ],
    "pipeline.ingest.tea_recapture": ["recapture_paid.parquet", "elr_lists.parquet"],
    "pipeline.ingest.census": ["saipe.parquet", "acs.parquet"],
    "pipeline.ingest.tea_tapr": ["tapr.parquet"],
    "pipeline.ingest.brb": ["brb_issuance.parquet", "brb_cab_cib.parquet"],
    "pipeline.ingest.nces_schools": ["school_points.parquet"],
    "pipeline.ingest.fred_cpi": ["cpi_school_year.parquet"],
    "pipeline.ingest.nces": [
        "boundaries.parquet",
        "ccd_lea.parquet",
        "edge_lea.parquet",
        "askted.parquet",
    ],
}
# SQL layers in dependency order; files inside a layer run in this explicit order
SQL_ORDER = {
    "ref": None,  # alphabetical
    "staging": None,
    "core": [
        "dim_district.sql",
        "fct_enrollment_district_year.sql",
        "fct_spending_district_year.sql",
        "fct_revenue_district_year.sql",
        "fct_wealth_district_year.sql",
    ],
    "marts": [
        "mart_district_year.sql",
        "mart_districts.sql",
        "mart_recapture.sql",
        "mart_tax_rates.sql",
        "mart_property_mix.sql",
        "mart_money_cycle_state_year.sql",
        "mart_charters_state_year.sql",
        "mart_debt.sql",
        "mart_campuses.sql",
        "mart_growth_capital.sql",
    ],
}
ANALYSIS = ["pipeline.analysis.equity", "pipeline.analysis.regression", "pipeline.analysis.peers"]


def run_ingest(refresh: bool) -> None:
    for module, outputs in INGEST.items():
        if refresh or not all((PROCESSED / o).exists() for o in outputs):
            print(f"-- ingest {module}")
            importlib.import_module(module).main()
    geo = ROOT / "data" / "geo" / "tx_districts_simplified.geojson"
    if refresh or not geo.exists():
        importlib.import_module("pipeline.clean.geo").build()


def sql_files() -> list[Path]:
    files = []
    for layer, order in SQL_ORDER.items():
        d = SQL / layer
        names = order if order is not None else sorted(p.name for p in d.glob("*.sql"))
        files += [d / n for n in names]
    extra = {p for layer in SQL_ORDER for p in (SQL / layer).glob("*.sql")} - set(files)
    if extra:
        raise RuntimeError(f"SQL files not in build order: {sorted(map(str, extra))}")
    return files


def build_warehouse() -> duckdb.DuckDBPyConnection:
    WAREHOUSE.unlink(missing_ok=True)
    con = duckdb.connect(str(WAREHOUSE))
    con.execute(f"SET VARIABLE processed = '{PROCESSED.as_posix()}'")
    for f in sql_files():
        t0 = time.perf_counter()
        con.execute(f.read_text())
        print(f"   {f.relative_to(ROOT)}  ({time.perf_counter() - t0:.1f}s)")
    return con


def run_analysis(con: duckdb.DuckDBPyConnection) -> None:
    for module in ANALYSIS:
        print(f"-- analysis {module}")
        importlib.import_module(module).run(con)


def export_marts(con: duckdb.DuckDBPyConnection) -> list[str]:
    MARTS.mkdir(parents=True, exist_ok=True)
    names = [
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'mart_%' ORDER BY 1"
        ).fetchall()
    ]
    for old in MARTS.glob("mart_*.parquet"):
        if old.stem not in names:
            old.unlink()
    for n in names:
        con.execute(
            f"COPY {n} TO '{(MARTS / f'{n}.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)"
        )
    total = sum((MARTS / f"{n}.parquet").stat().st_size for n in names)
    print(f"-- exported {len(names)} marts to data/marts ({total / 1e6:.1f} MB)")
    return names


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args(argv)
    print("== 1. ingest ==")
    run_ingest(args.refresh)
    print("== 2. warehouse (DuckDB SQL) ==")
    con = build_warehouse()
    print("== 3. analysis ==")
    run_analysis(con)
    print("== 4. export ==")
    export_marts(con)
    print("== 5. data-quality checks ==")
    from pipeline import qa

    ok = qa.run(con)
    from pipeline import qa_reports

    qa_reports.run(con)
    con.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
