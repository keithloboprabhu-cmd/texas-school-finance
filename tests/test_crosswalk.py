"""Crosswalk: TEA CDN <-> NCES LEAID <-> Census GEOID."""

import duckdb
import pandas as pd
from conftest import MARTS, ROOT, needs

WAREHOUSE = ROOT / "data" / "warehouse.duckdb"


@needs(MARTS / "mart_districts.parquet")
def test_committed_marts_have_valid_ids():
    d = pd.read_parquet(MARTS / "mart_districts.parquet")
    assert d.cdn.str.fullmatch(r"\d{6}").all(), "CDNs must be 6-digit zero-padded strings"
    assert d.geoid.str.fullmatch(r"48\d{5}").all(), "GEOIDs must be Texas FIPS 48 + 5 digits"
    assert d.cdn.is_unique and d.geoid.is_unique
    assert d.leaid.equals(d.geoid)


@needs(WAREHOUSE)
def test_crosswalk_match_rate():
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    con.execute(f"SET VARIABLE processed = '{(ROOT / 'data' / 'processed').as_posix()}'")
    n, matched, saipe, acs = con.execute("""
        SELECT count(*), count(*) FILTER (WHERE in_analysis),
               count(*) FILTER (WHERE geoid IN (SELECT geoid FROM stg_saipe)),
               count(*) FILTER (WHERE geoid IN (SELECT geoid FROM stg_acs))
        FROM dim_district
        WHERE is_isd AND valid_to = (SELECT max(year) FROM stg_peims_summarized)""").fetchone()
    assert matched / n >= 0.98
    assert saipe / n >= 0.98
    assert acs / n >= 0.98
    assert con.execute("SELECT count(*) FROM dim_district WHERE leaid_conflict").fetchone()[0] == 0
    con.close()


@needs(ROOT / "data" / "qa" / "unmatched.csv")
def test_unmatched_logged():
    un = pd.read_csv(ROOT / "data" / "qa" / "unmatched.csv", dtype=str)
    assert {"cdn", "district_name", "reason"} <= set(un.columns)
    assert un.reason.notna().all()
