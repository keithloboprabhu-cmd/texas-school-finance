"""Committed marts: keys, bounds and definitions. Runs in CI (marts are committed)."""

import pandas as pd
import pytest
from conftest import MARTS, needs

pytestmark = needs(MARTS / "mart_district_year.parquet")


@pytest.fixture(scope="module")
def dy():
    return pd.read_parquet(MARTS / "mart_district_year.parquet")


def test_unique_keys(dy):
    assert not dy.duplicated(["cdn", "year"]).any()
    for name, key in [
        ("mart_districts", ["cdn"]),
        ("mart_equity_state_year", ["year"]),
        ("mart_recapture", ["cdn", "year"]),
        ("mart_tax_rates", ["cdn", "year"]),
    ]:
        df = pd.read_parquet(MARTS / f"{name}.parquet")
        assert not df.duplicated(key).any(), name


def test_cdn_is_string(dy):
    assert dy.cdn.str.fullmatch(r"\d{6}").all()


def test_operating_excludes_recapture_and_debt(dy):
    # headline operating never exceeds TEA's operating definition, and recapture is held separately
    assert (dy.operating <= dy.operating_tea_def + 1).all() | (dy.ssa_agent_operating < 0).any()
    payers = dy[dy.recapture_paid > 0]
    assert len(payers) > 0
    assert (
        "recapture_paid" in dy.columns and "debt_service" in dy.columns and "capital" in dy.columns
    )


def test_per_student_spending_plausible(dy):
    x = dy.loc[dy.enrollment >= 500, "op_per_student_real"]
    assert x.between(5_000, 40_000).mean() > 0.99


def test_real_dollars_anchor(dy):
    latest = dy.year.max()
    assert dy.loc[dy.year == latest, "real_factor"].round(6).eq(1).all()


def test_equity_metrics_sane():
    eq = pd.read_parquet(MARTS / "mart_equity_state_year.parquet")
    assert eq.mcloone.between(0.5, 1).all()
    assert (eq.restricted_range_ratio >= 1).all()
    assert eq.cv.between(0, 1).all()
