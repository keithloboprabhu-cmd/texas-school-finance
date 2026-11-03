"""Tiny runtime statistics (no statsmodels in the deployed app)."""

from __future__ import annotations

import numpy as np


def wls_hc1(x, y, w):
    """Weighted least squares of y on [1, x] with HC1 standard errors.
    Returns slope, (ci_lo, ci_hi), r2, n. Matches statsmodels WLS(...).fit(cov_type='HC1')."""
    x, y, w = (np.asarray(a, float) for a in (x, y, w))
    X = np.column_stack([np.ones_like(x), x])
    sw = np.sqrt(w)
    Xw, yw = X * sw[:, None], y * sw
    beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    e = yw - Xw @ beta
    n, k = Xw.shape
    bread = np.linalg.inv(Xw.T @ Xw)
    meat = (Xw * e[:, None] ** 2).T @ Xw
    cov = bread @ meat @ bread * n / (n - k)
    se = np.sqrt(np.diag(cov))
    ybar = np.sum(w * y) / np.sum(w)
    r2 = 1 - np.sum(w * (y - X @ beta) ** 2) / np.sum(w * (y - ybar) ** 2)
    return beta[1], (beta[1] - 1.96 * se[1], beta[1] + 1.96 * se[1]), r2, n
