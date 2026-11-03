"""Compute the README's findings from the committed marts and write them between the
<!-- findings:start --> and <!-- findings:end --> markers. Run after `make data`."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
APP_SQL = ROOT / "sql" / "app"


def sy(y: int) -> str:
    return f"{y - 1}-{str(y)[2:]}"


def big(v: float) -> str:
    return f"${v / 1e9:.2f}B" if v >= 1e9 else f"${v / 1e6:.0f}M"


def main() -> None:
    con = duckdb.connect()
    for p in (ROOT / "data" / "marts").glob("*.parquet"):
        con.execute(f"CREATE TABLE {p.stem} AS SELECT * FROM read_parquet('{p.as_posix()}')")
    latest = con.execute("SELECT max(year) FROM mart_district_year").fetchone()[0]
    q = {
        n: (APP_SQL / f"{n}.sql").read_text().strip()
        for n in ["findings", "finding_outliers", "finding_recapture"]
    }
    eq = con.execute(q["findings"]).df()
    first, last = eq.iloc[0], eq.iloc[-1]
    ctrl = con.execute(
        "SELECT coef, ci_lo, ci_hi FROM mart_model_latest WHERE model='controlled' AND term='log_wealth'"
    ).fetchone()
    out = con.execute(q["finding_outliers"]).df().set_index("direction")
    over = out.loc["over"]
    rec = con.execute(q["finding_recapture"], {"year": latest}).df().iloc[0]

    text = f"""### 1. Property wealth barely predicts operating spending

In {sy(int(last.year))}, a district with 10% more property wealth per student spent about **{abs(last.elasticity * 10):.2f}%**
{"more" if last.elasticity >= 0 else "less"} per student (95% CI {last.elasticity_lo * 10:+.2f}% to {last.elasticity_hi * 10:+.2f}%; n = {int(last.elasticity_n):,}
districts, enrollment-weighted). In {sy(int(first.year))} the figure was {first.elasticity * 10:+.2f}%. The spending gap
between the wealthiest and poorest fifths of students went from {first.quintile_gap_ratio - 1:+.1%} to
{last.quintile_gap_ratio - 1:+.1%}. After controlling for size, student need, locale and density, the elasticity is a
small positive {ctrl[0]:+.3f} (95% CI {ctrl[1]:+.3f} to {ctrl[2]:+.3f}).

```sql
{q["findings"]}
```

### 2. The biggest over-spenders are tiny rural districts

All **{int(over.n_small)} of the {int(over.n)}** districts that spend furthest above the controlled model's prediction
in {sy(int(over.year))} have fewer than 500 students (median {over.median_enrollment:,.0f}) and are rural. They spend a
median ${over.median_actual:,.0f} per student against ${over.median_predicted:,.0f} predicted. Statewide,
{over.share_small_statewide:.0%} of districts are that small. Size, more than wealth, marks the extremes.

```sql
{q["finding_outliers"]}
```

### 3. A third of recapture comes from mineral wealth

Districts paid **{big(rec.total_paid)}** in recapture in {sy(int(latest))}. Of that, {big(rec.paid_by_mineral_majority)}
({rec.paid_by_mineral_majority / rec.total_paid:.0%}) came from the {int(rec.payers_mineral_majority)} paying districts
where oil, gas and other minerals are most of the tax base, and {int(rec.payers_below_median_income)} of the
{int(rec.payers)} payers have below-median household income. Property-rich is not the same as rich residents.

```sql
{q["finding_recapture"].replace("$year", str(int(latest)))}
```
"""
    readme = ROOT / "README.md"
    body = readme.read_text()
    body = re.sub(
        r"<!-- findings:start -->.*<!-- findings:end -->",
        lambda m: f"<!-- findings:start -->\n{text}\n<!-- findings:end -->",
        body,
        flags=re.S,
    )
    readme.write_text(body)
    print(text)


if __name__ == "__main__":
    main()
