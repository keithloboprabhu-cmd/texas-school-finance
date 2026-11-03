"""Statistics helpers and the elasticity estimator on synthetic data with known answers."""

import numpy as np
import pandas as pd
import pytest

from pipeline.analysis.equity import elasticity
from pipeline.analysis.stats import mcloone, weighted_quintiles, wmean, wquantile, wstd


def test_weighted_basics():
    x, w = np.array([1.0, 2.0, 3.0]), np.array([1.0, 1.0, 2.0])
    assert wmean(x, w) == pytest.approx(2.25)
    assert wstd([5, 5, 5], [1, 2, 3]) == 0
    assert wquantile([1, 2, 3, 4], [1, 1, 1, 1], 0.5) == 2


def test_mcloone_equal_spending_is_one():
    assert mcloone([10, 10, 10, 10], [1, 2, 3, 4]) == pytest.approx(1.0)


def test_mcloone_known_value():
    # students: 1 at 5, 1 at 10, 2 at 20 -> weighted median 10; below median: one student at 5
    assert mcloone([5, 10, 20], [1, 1, 2]) == pytest.approx(0.5)


def test_quintiles_split_students_evenly():
    rng = np.random.default_rng(0)
    x, w = rng.lognormal(size=2000), rng.integers(1, 1000, size=2000)
    q = weighted_quintiles(x, w)
    shares = pd.Series(w).groupby(q).sum() / w.sum()
    assert set(q) == {1, 2, 3, 4, 5}
    assert np.allclose(shares, 0.2, atol=0.02)
    assert pd.Series(x).groupby(q).max().is_monotonic_increasing


def test_elasticity_recovers_known_slope():
    rng = np.random.default_rng(1)
    wealth = rng.lognormal(12, 1, 800)
    spend = np.exp(8 + 0.3 * np.log(wealth) + rng.normal(0, 0.05, 800))
    df = pd.DataFrame(
        {
            "wealth_per_student_real": wealth,
            "op_per_student_real": spend,
            "enrollment": rng.integers(50, 5000, 800),
        }
    )
    b, lo, hi, r2, n = elasticity(df)
    assert lo < 0.3 < hi
    assert b == pytest.approx(0.3, abs=0.02)
    assert n == 800


def test_runtime_wls_matches_statsmodels():
    import statsmodels.api as sm

    from ui.stats import wls_hc1

    rng = np.random.default_rng(3)
    x = rng.normal(size=300)
    y = 1 + 0.5 * x + rng.normal(size=300) * (1 + np.abs(x))
    w = rng.integers(1, 100, 300)
    fit = sm.WLS(y, sm.add_constant(x), weights=w).fit(cov_type="HC1")
    b, (lo, hi), r2, n = wls_hc1(x, y, w)
    assert b == pytest.approx(fit.params[1])
    assert lo == pytest.approx(fit.params[1] - 1.96 * fit.bse[1])
    assert r2 == pytest.approx(fit.rsquared)
