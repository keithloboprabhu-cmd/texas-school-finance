"""Statewide spending equity by school year -> mart_equity_state_year.

Universe: current and consolidated/closed ISDs (mart_district_year), enrollment > 0 and operating
spending > 0, excluding districts flagged enrollment_caution (large virtual or non-resident enrollment). All metrics are enrollment-weighted and use real operating spending per student.
Wealth-based metrics need property values, which start with school year 2010-11 (tax year 2010).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from pipeline.analysis.stats import mcloone, weighted_quintiles, wmean, wquantile, wstd


def elasticity(df: pd.DataFrame):
    """WLS of log(spend) on log(wealth), enrollment weights, HC1 errors."""
    X = sm.add_constant(np.log(df.wealth_per_student_real))
    fit = sm.WLS(np.log(df.op_per_student_real), X, weights=df.enrollment).fit(cov_type="HC1")
    b = fit.params.iloc[1]
    lo, hi = fit.conf_int().iloc[1]
    return b, lo, hi, fit.rsquared, int(fit.nobs)


def run(con) -> pd.DataFrame:
    df = con.execute("""
        SELECT y.year, y.cdn, y.enrollment, y.op_per_student_real, y.wealth_per_student_real
        FROM mart_district_year y LEFT JOIN mart_districts d USING (cdn)
        WHERE y.enrollment > 0 AND y.operating > 0 AND NOT coalesce(d.enrollment_caution, FALSE)
    """).df()
    rows = []
    for year, g in df.groupby("year"):
        x, w = g.op_per_student_real.values, g.enrollment.values
        ok = (x >= 5000) & (x <= 60000)
        row = {
            "year": int(year),
            "n_districts": len(g),
            "students": int(w.sum()),
            "mean_spend": wmean(x, w),
            "median_spend": wquantile(x, w, 0.5),
            "cv": wstd(x, w) / wmean(x, w),
            # CV over district-years inside the $5k-$60k plausibility bounds (out-of-bounds values are
            # logged in data/qa/spending_bounds_log.csv); one anomalous district can move the CV.
            "cv_bounded": wstd(x[ok], w[ok]) / wmean(x[ok], w[ok]),
            "mcloone": mcloone(x, w),
            "p05_spend": wquantile(x, w, 0.05),
            "p95_spend": wquantile(x, w, 0.95),
        }
        row["restricted_range_ratio"] = row["p95_spend"] / row["p05_spend"]
        gw = g[g.wealth_per_student_real > 0]
        if len(gw) > 100:
            lx, ly = np.log(gw.wealth_per_student_real), np.log(gw.op_per_student_real)
            ww = gw.enrollment.values
            cov = np.cov(lx, ly, aweights=ww)
            row["wealth_spend_corr"] = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
            b, lo, hi, r2, n = elasticity(gw)
            row.update(
                elasticity=b, elasticity_lo=lo, elasticity_hi=hi, elasticity_r2=r2, elasticity_n=n
            )
            q = weighted_quintiles(gw.wealth_per_student_real.values, ww)
            top = wmean(gw.op_per_student_real[q == 5], ww[q == 5])
            bot = wmean(gw.op_per_student_real[q == 1], ww[q == 1])
            row.update(
                top_quintile_spend=top,
                bottom_quintile_spend=bot,
                quintile_gap_ratio=top / bot,
                quintile_gap_dollars=top - bot,
            )
        rows.append(row)
    out = pd.DataFrame(rows)
    con.register("equity_df", out)
    con.execute("CREATE OR REPLACE TABLE mart_equity_state_year AS SELECT * FROM equity_df")
    con.unregister("equity_df")
    print(f"   mart_equity_state_year: {len(out)} years")
    return out
