"""Guided tour of the Atlas: each stop sets a map state and states one computed number."""

from __future__ import annotations

import pandas as pd

from ui import data
from ui.components import big_money, pct, sy


def stops(year: int) -> list[dict]:
    eq = data.query("findings")
    first, last = eq.iloc[0], eq.iloc[-1]
    layers = data.query("atlas_layers", year=year)
    rec = data.query("finding_recapture", year=year).iloc[0]
    out = data.query("finding_outliers")
    over = out[out.direction == "over"].iloc[0]
    debt = data.query("debt_state_year")
    d0, d1 = debt.iloc[0], debt.iloc[-1]
    camp = data.query("finding_campuses").iloc[0]
    mineral = layers.dropna(subset=["mineral_share"])
    top_mineral = mineral.sort_values("mineral_share", ascending=False).head(25)
    return [
        dict(
            title="The statewide pattern",
            view="Bivariate",
            metric="wealth",
            text=(
                "Each district is coloured by thirds of property wealth and of spending per student. "
                "If wealth drove spending, the map would run from light grey to dark purple."
            ),
            number=f"{last.elasticity:+.3f}",
            number_label=f"wealth elasticity of spending, {sy(int(last.year))}",
        ),
        dict(
            title="Mineral wealth",
            view="Single metric",
            metric="mineral",
            text=(
                "In many West Texas and Gulf Coast districts most taxable value is oil, gas and minerals. "
                "That wealth belongs to the tax base, not to residents."
            ),
            number=pct(top_mineral.mineral_share.median(), 0),
            number_label="median mineral share among the 25 most mineral-heavy districts",
            focus=(float(top_mineral.lat.median()), float(top_mineral.lon.median()), 6.2),
        ),
        dict(
            title="Recapture",
            view="Single metric",
            metric="recapture",
            text="Districts above the state's wealth threshold send part of their local revenue to the state.",
            number=big_money(rec.total_paid),
            number_label=f"paid by {int(rec.payers)} districts in {sy(year)}",
        ),
        dict(
            title="Where Texas is growing",
            view="Single metric",
            metric="growth",
            text="Enrollment grows in suburban rings around Houston, Dallas-Fort Worth, Austin and San Antonio.",
            number=f"{int(camp.new_open):,}",
            number_label="ISD campuses opened since 2016-17 and still open",
        ),
        dict(
            title="Borrowing to build",
            view="Single metric",
            metric="debt",
            text="Tax-supported school debt is concentrated in growing districts.",
            number=big_money(d1.tax_supported_principal),
            number_label=(
                f"ISD tax-supported principal, FY{int(d1.fiscal_year)} "
                f"(FY{int(d0.fiscal_year)}: {big_money(d0.tax_supported_principal)}, nominal)"
            ),
        ),
        dict(
            title="The outliers",
            view="Single metric",
            metric="residual",
            text=(
                "After accounting for wealth, size, need, locale and density, the districts spending most "
                "above prediction are all very small and rural."
            ),
            number=f"{int(over.n_small)} of {int(over.n)}",
            number_label="top over-spenders with fewer than 500 students",
        ),
        dict(
            title="How equity changed",
            view="Bivariate",
            metric="wealth",
            text="Spending is less tied to property wealth than it was in the early 2010s.",
            number=f"{(first.quintile_gap_ratio - 1):+.1%} → {(last.quintile_gap_ratio - 1):+.1%}",
            number_label=(
                f"spending gap, wealthiest vs. poorest fifth of students, {sy(int(first.year))} → "
                f"{sy(int(last.year))}"
            ),
        ),
    ]


def as_frame(year: int) -> pd.DataFrame:
    return pd.DataFrame(stops(year))
