"""Small, tested helpers for enrollment-weighted statistics."""

from __future__ import annotations

import numpy as np


def wmean(x, w) -> float:
    x, w = np.asarray(x, float), np.asarray(w, float)
    return float(np.sum(x * w) / np.sum(w))


def wstd(x, w) -> float:
    x, w = np.asarray(x, float), np.asarray(w, float)
    m = wmean(x, w)
    return float(np.sqrt(np.sum(w * (x - m) ** 2) / np.sum(w)))


def wquantile(x, w, q: float) -> float:
    """Weighted quantile: smallest x whose cumulative weight share reaches q (step function)."""
    x, w = np.asarray(x, float), np.asarray(w, float)
    order = np.argsort(x)
    x, w = x[order], w[order]
    cw = np.cumsum(w) / np.sum(w)
    return float(x[np.searchsorted(cw, q, side="left")])


def mcloone(x, w) -> float:
    """McLoone index: spending on students below the (weighted) median divided by what it would be
    if each of those students received the median. 1.0 = no inequality in the bottom half."""
    x, w = np.asarray(x, float), np.asarray(w, float)
    med = wquantile(x, w, 0.5)
    below = x < med
    if not below.any():  # nobody below the median: no inequality in the bottom half
        return 1.0
    return float(np.sum(x[below] * w[below]) / (med * np.sum(w[below])))


def weighted_quintiles(x, w) -> np.ndarray:
    """Assign quintiles 1..5 so that each holds about 20% of the total weight (students)."""
    x, w = np.asarray(x, float), np.asarray(w, float)
    order = np.argsort(x, kind="stable")
    cw = np.cumsum(w[order]) / np.sum(w)
    q = np.empty(len(x), dtype=int)
    q[order] = np.minimum(5, np.floor((cw - w[order] / (2 * np.sum(w))) * 5).astype(int) + 1)
    return q
