"""BRB <-> CDN crosswalk and campus detection."""

import pandas as pd
from conftest import MARTS, PROCESSED, ROOT, needs


@needs(ROOT / "data" / "qa" / "brb_crosswalk_review.csv")
def test_brb_crosswalk_hand_reviewed():
    df = pd.read_csv(ROOT / "data" / "qa" / "brb_crosswalk_review.csv", dtype=str)
    assert df.cdn.str.fullmatch(r"\d{6}").all()
    assert df.tea_name.notna().all(), "every BRB issuer maps to a TEA district"
    assert df.review.str.startswith("match").all(), "every name difference was reviewed"
    assert df.cdn.is_unique and df.brb_id.is_unique


@needs(PROCESSED / "school_points.parquet")
def test_ncessch_prefix_is_leaid():
    d = pd.read_parquet(PROCESSED / "school_points.parquet")
    f = d[d.leaid_from_file]
    assert len(f) > 10_000
    assert (f.ncessch.str[:7] == f.leaid).all()


@needs(MARTS / "mart_campuses.parquet")
def test_campus_marts():
    c = pd.read_parquet(MARTS / "mart_campuses.parquet")
    assert c.ncessch.is_unique
    assert c.first_year.min() == 2016  # baseline year: campuses present in 2015-16 are not "new"
    assert not c.loc[c.first_year == 2016, "is_new"].any()
    g = pd.read_parquet(MARTS / "mart_growth_capital.parquet")
    assert g.cdn.is_unique


@needs(MARTS / "mart_debt_district.parquet")
def test_debt_marts():
    d = pd.read_parquet(MARTS / "mart_debt_district.parquet")
    assert d.cdn.is_unique
    assert (d.cab_share_principal.dropna().between(0, 1)).all()
    w = pd.read_parquet(MARTS / "mart_maturity_wall.parquet")
    assert w.final_maturity_year.min() >= w.as_of_fiscal_year.min() - 1
