"""Wealth vs. spending models for the latest school year -> mart_model_latest, mart_outliers_latest.

Simple model:     log(spend) ~ log(wealth)                        (WLS, enrollment weights, HC1)
Controlled model: + log(enrollment) + econ. disadvantaged share + English learner share
                  + special education share + locale (City/Suburb/Town/Rural) + log(students per sq. mile)
Outliers: standardized residuals from the controlled model (residual / weighted residual SD).
Sensitivity: Huber robust regression (statsmodels RLM, HuberT) on the same specification; a district
is flagged `method_sensitive` if it is a top/bottom-15 outlier under one method but not the other.
Demographic shares are TAPR 2023-24 (the 2024-25 TAPR was not yet published).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

TOP_N = 15
CONTROLS = [
    "log_enrollment",
    "econ_disadv_pct",
    "english_learners_pct",
    "special_ed_pct",
    "log_density",
]


def _design(df: pd.DataFrame, controlled: bool) -> pd.DataFrame:
    X = pd.DataFrame({"log_wealth": np.log(df.wealth_per_student_real)}, index=df.index)
    if controlled:
        X = X.join(df[CONTROLS])
        X = X.join(
            pd.get_dummies(df.locale, prefix="locale", drop_first=False, dtype=float).drop(
                columns="locale_City", errors="ignore"
            )
        )
    return sm.add_constant(X)


def load(con) -> pd.DataFrame:
    df = con.execute("""
        SELECT y.cdn, y.year, y.district_name, y.county, y.esc_region, y.locale, y.enrollment,
               y.small_district, y.op_per_student_real, y.wealth_per_student_real,
               y.recapture_designated, y.recapture_paid,
               d.econ_disadv_pct, d.english_learners_pct, d.special_ed_pct, d.land_sq_miles,
               d.median_household_income, d.child_poverty_rate
        FROM mart_district_year y JOIN mart_districts d USING (cdn)
        WHERE y.is_current AND NOT d.enrollment_caution AND y.year = (SELECT max(year) FROM mart_district_year)
          AND y.enrollment > 0 AND y.operating > 0 AND y.op_per_student_real IS NOT NULL AND y.wealth_per_student_real > 0
    """).df()
    df["log_enrollment"] = np.log(df.enrollment)
    df["log_density"] = np.log(df.enrollment / df.land_sq_miles)
    return df.dropna(subset=CONTROLS + ["locale"]).reset_index(drop=True)


def fit_models(df: pd.DataFrame):
    y = np.log(df.op_per_student_real)
    simple = sm.WLS(y, _design(df, False), weights=df.enrollment).fit(cov_type="HC1")
    ctrl = sm.WLS(y, _design(df, True), weights=df.enrollment).fit(cov_type="HC1")
    huber = sm.RLM(y, _design(df, True), M=sm.robust.norms.HuberT()).fit()
    return simple, ctrl, huber


def _hints(r: pd.Series, q: dict) -> str:
    """Data-only 'why it might be' hints (no outside knowledge)."""
    h = []
    if r.enrollment < 500:
        h.append("very small district")
    if r.log_density <= q["density_p10"]:
        h.append("sparse (few students per square mile)")
    if r.locale == "Rural":
        h.append("rural")
    if r.wealth_per_student_real >= q["wealth_p90"]:
        h.append("high property wealth")
    if pd.notna(r.median_household_income) and r.median_household_income <= q["income_p25"]:
        h.append("low household income")
    if r.special_ed_pct >= q["sped_p90"]:
        h.append("large special-education share")
    if r.econ_disadv_pct >= q["econ_p90"]:
        h.append("high share of economically disadvantaged students")
    if r.recapture_paid > 0:
        h.append("pays recapture")
    return "; ".join(h[:3])


def run(con) -> None:
    df = load(con)
    simple, ctrl, huber = fit_models(df)

    coef_rows = []
    for name, fit in [("simple", simple), ("controlled", ctrl), ("huber", huber)]:
        ci = fit.conf_int()
        for term in fit.params.index:
            coef_rows.append(
                {
                    "model": name,
                    "term": term,
                    "coef": fit.params[term],
                    "std_err": fit.bse[term],
                    "ci_lo": ci.loc[term, 0],
                    "ci_hi": ci.loc[term, 1],
                    "p_value": fit.pvalues[term],
                    "n": int(fit.nobs),
                    "r2": getattr(fit, "rsquared", np.nan),
                    "year": int(df.year.iloc[0]),
                }
            )
    coefs = pd.DataFrame(coef_rows)

    resid = ctrl.resid
    sd = np.sqrt(np.sum(df.enrollment * resid**2) / np.sum(df.enrollment))
    df["predicted_real"] = np.exp(ctrl.fittedvalues)
    df["residual_log"] = resid
    df["std_residual"] = resid / sd
    df["huber_std_residual"] = huber.resid / huber.scale

    def extremes(col):
        s = df[col]
        return set(df.loc[s.nlargest(TOP_N).index, "cdn"]), set(
            df.loc[s.nsmallest(TOP_N).index, "cdn"]
        )

    over, under = extremes("std_residual")
    h_over, h_under = extremes("huber_std_residual")
    q = {
        "density_p10": df.log_density.quantile(0.1),
        "wealth_p90": df.wealth_per_student_real.quantile(0.9),
        "income_p25": df.median_household_income.quantile(0.25),
        "sped_p90": df.special_ed_pct.quantile(0.9),
        "econ_p90": df.econ_disadv_pct.quantile(0.9),
    }
    df["direction"] = np.where(
        df.cdn.isin(over), "over", np.where(df.cdn.isin(under), "under", None)
    )
    df["method_sensitive"] = (df.cdn.isin(over) != df.cdn.isin(h_over)) | (
        df.cdn.isin(under) != df.cdn.isin(h_under)
    )
    df["rank_over"] = df.std_residual.rank(ascending=False).astype(int)
    df["rank_under"] = df.std_residual.rank(ascending=True).astype(int)
    df["hint"] = df.apply(_hints, axis=1, q=q)
    out = df[
        [
            "cdn",
            "year",
            "district_name",
            "county",
            "esc_region",
            "locale",
            "enrollment",
            "small_district",
            "op_per_student_real",
            "predicted_real",
            "residual_log",
            "std_residual",
            "huber_std_residual",
            "direction",
            "rank_over",
            "rank_under",
            "method_sensitive",
            "recapture_designated",
            "recapture_paid",
            "wealth_per_student_real",
            "econ_disadv_pct",
            "special_ed_pct",
            "hint",
        ]
    ]
    for name, frame in [("mart_model_latest", coefs), ("mart_outliers_latest", out)]:
        con.register("tmp_df", frame)
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM tmp_df")
        con.unregister("tmp_df")
    b = simple.params["log_wealth"]
    print(
        f"   simple elasticity {b:.3f} (n={int(simple.nobs)}), controlled {ctrl.params['log_wealth']:.3f}; "
        f"outliers over={len(over)} under={len(under)}, method-sensitive={int(out.method_sensitive.sum())}"
    )
