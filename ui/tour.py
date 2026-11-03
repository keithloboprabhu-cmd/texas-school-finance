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
                "Each district's color shows how its property wealth and its spending per student compare "
                "with other districts. If wealth drove spending, most districts would be light gray or dark purple."
            ),
            number=f"{last.elasticity * 10:+.2f}%",
            number_label=f"extra spending per student for every 10% more property wealth, {sy(int(last.year))}",
        ),
        dict(
            title="Mineral wealth",
            view="Single metric",
            metric="mineral",
            text=(
                "In some districts, most of the taxable property is oil, gas and minerals. That makes the district "
                "look rich on paper even when the people who live there are not."
            ),
            number=pct(top_mineral.mineral_share.median(), 0),
            number_label="typical share of property that is minerals, in the 25 most mineral-heavy districts",
            focus=(float(top_mineral.lat.median()), float(top_mineral.lon.median()), 6.2),
        ),
        dict(
            title="Recapture",
            view="Single metric",
            metric="recapture",
            text=(
                "When a district's local taxes raise more than the state formula allows, it sends the extra to "
                "the state. This is called recapture."
            ),
            number=big_money(rec.total_paid),
            number_label=f"sent to the state by {int(rec.payers)} districts in {sy(year)}",
        ),
        dict(
            title="Where Texas is growing",
            view="Single metric",
            metric="growth",
            text="Clay districts gained students over the last five years. Teal districts lost students.",
            number=f"{int(camp.new_open):,}",
            number_label="school district campuses opened since 2016-17 that are still open",
        ),
        dict(
            title="Borrowing to build",
            view="Single metric",
            metric="debt",
            text="School districts borrow to build schools, and voters approve the debt. Darker districts owe more per student.",
            number=big_money(d1.tax_supported_principal),
            number_label=(
                f"voter-approved debt owed by Texas school districts in fiscal year {int(d1.fiscal_year)}, up from "
                f"{big_money(d0.tax_supported_principal)} in {int(d0.fiscal_year)} (not adjusted for inflation)"
            ),
        ),
        dict(
            title="The outliers",
            view="Single metric",
            metric="residual",
            text=(
                "We predicted each district's spending from its wealth, size, students and setting. The districts "
                "that spend the most above that prediction are all small and rural."
            ),
            number=f"{int(over.n_small)} of {int(over.n)}",
            number_label="biggest over-spenders that have fewer than 500 students",
        ),
        dict(
            title="How equity changed",
            view="Bivariate",
            metric="wealth",
            text="Spending depends less on property wealth than it did in the early 2010s.",
            number=f"{(first.quintile_gap_ratio - 1):+.1%} → {(last.quintile_gap_ratio - 1):+.1%}",
            number_label=(
                f"spending gap between students in the wealthiest and poorest fifth of districts, {sy(int(first.year))} → "
                f"{sy(int(last.year))}"
            ),
        ),
    ]


def as_frame(year: int) -> pd.DataFrame:
    return pd.DataFrame(stops(year))
