"""Reconciliation and spot checks against TEA's published Financial Actual Reports ("Actual PWR"
workbooks behind TEA's PEIMS Financial Standard Reports page):
https://tea.texas.gov/about-tea/state-funding/state-funding-reports-and-data/peims-financial-standard-reports

Writes data/qa/reconciliation.md and data/qa/spot_checks.md.
"""

from __future__ import annotations

import pandas as pd

from pipeline.ingest._http import RAW, ROOT, fetch

QA = ROOT / "data" / "qa"
_T = "https://tea.texas.gov"
PWR = {  # school-year ending -> TEA "Actual PWR" workbook
    2025: f"{_T}/about-tea/state-funding/state-funding-reports-and-data/actual2025-info-gen-all.xlsx",
    2021: f"{_T}/data-reports/financial-reports/school-finance-reports-and-data/2021-actual-pwr.xlsx",
    2017: f"{_T}/data-reports/financial-reports/school-finance-reports-and-data/2017-actual-pwr-1.xlsx",
}
# Looked up by name in dim_district (never hard-coded CDNs), plus one small rural district
SPOT_NAMES = ["AUSTIN ISD", "HOUSTON ISD", "DALLAS ISD", "EANES ISD"]


def _sheet(xl: pd.ExcelFile, suffix: str) -> pd.DataFrame:
    name = next(s for s in xl.sheet_names if s.strip().endswith(suffix))
    df = xl.parse(name, dtype=str)
    df["cdn"] = df["DISTRICT NUMBER"].str.lstrip("'").str.zfill(6)
    return df


def load_pwr(year: int) -> pd.DataFrame:
    path = fetch(PWR[year], RAW / "tea_fsr" / f"actual{year}_pwr.xlsx").path
    xl = pd.ExcelFile(path)
    af, enr = _sheet(xl, "AF Act"), _sheet(xl, "Enroll Act")
    op_col = next(
        c for c in af.columns if c.strip() == "AF Total Operating Expenditures by Function"
    )
    out = af[["cdn", "DISTRICT NAME", op_col]].rename(columns={op_col: "tea_operating"})
    out["tea_operating"] = pd.to_numeric(out.tea_operating)
    enr_col = next(c for c in enr.columns if c.strip().upper() == "ENROLLMENT")
    out = out.merge(enr[["cdn", enr_col]].rename(columns={enr_col: "tea_enrollment"}), on="cdn")
    out["tea_enrollment"] = pd.to_numeric(out.tea_enrollment)
    out["year"] = year
    return out


def run(con) -> None:
    QA.mkdir(parents=True, exist_ok=True)
    ours = con.execute("""
        SELECT f.cdn, f.year, f.operating_tea_def, f.operating, e.enrollment
        FROM fct_spending_district_year f JOIN fct_enrollment_district_year e USING (cdn, year)""").df()
    lines = [
        "# Reconciliation with TEA published totals",
        "",
        "Statewide operating expenditures (TEA definition: all funds, objects 6100-6400, operating "
        "functions, excluding capital projects funds) from this pipeline versus TEA's Financial Actual "
        "Report workbooks ('Actual PWR', column *AF Total Operating Expenditures by Function*), over "
        "the non-charter districts present in both. Tolerance: +/-2%.",
        "",
        "| School year | Districts | Pipeline ($) | TEA published ($) | Difference | Within 2% |",
        "|---|---:|---:|---:|---:|:---:|",
    ]
    pwr_all = {}
    for year in sorted(PWR):
        pwr = load_pwr(year)
        pwr_all[year] = pwr
        m = ours[ours.year == year].merge(pwr, on=["cdn", "year"])
        a, b = m.operating_tea_def.sum(), m.tea_operating.sum()
        diff = a / b - 1
        lines.append(
            f"| {year - 1}-{str(year)[2:]} | {len(m):,} | {a:,.0f} | {b:,.0f} | {diff:+.3%} | {'yes' if abs(diff) <= 0.02 else 'NO'} |"
        )
    (QA / "reconciliation.md").write_text("\n".join(lines) + "\n")

    latest = max(PWR)
    pwr = pwr_all[latest]
    rural = con.execute(f"""
        SELECT y.cdn FROM mart_district_year y
        WHERE y.year = {latest} AND y.is_current AND y.locale = 'Rural' AND y.enrollment BETWEEN 100 AND 300
        ORDER BY y.enrollment, y.cdn LIMIT 1""").fetchone()[0]
    named = con.execute(
        "SELECT cdn FROM dim_district WHERE upper(district_name) IN (SELECT unnest(?)) ORDER BY district_name",
        [SPOT_NAMES],
    ).fetchall()
    assert len(named) == len(SPOT_NAMES), "spot-check district not found by name"
    cdns = [r[0] for r in named] + [rural]
    m = ours[(ours.year == latest) & ours.cdn.isin(cdns)].merge(pwr, on=["cdn", "year"])
    rows = [
        "# District spot checks",
        "",
        f"School year {latest - 1}-{str(latest)[2:]}. TEA figures come from TEA's Financial Actual Report "
        "workbook (operating expenditures by function, all funds; enrollment from the same workbook). "
        "'Headline' is this project's operating spending, which additionally removes shared services "
        "arrangement fiscal-agent funds.",
        "",
        "| District | CDN | Enrollment (TEA) | TEA operating per student | Pipeline, TEA definition | Diff | Pipeline headline | Headline vs TEA |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in (
        m.set_index("cdn").loc[[c for c in cdns if c in set(m.cdn)]].reset_index().iterrows()
    ):
        tea_pp = r.tea_operating / r.tea_enrollment
        ours_pp = r.operating_tea_def / r.enrollment
        head_pp = r.operating / r.enrollment
        rows.append(
            f"| {r['DISTRICT NAME']} | {r.cdn} | {r.tea_enrollment:,.0f} | ${tea_pp:,.0f} | ${ours_pp:,.0f} | "
            f"{ours_pp / tea_pp - 1:+.2%} | ${head_pp:,.0f} | {head_pp / tea_pp - 1:+.2%} |"
        )
    (QA / "spot_checks.md").write_text("\n".join(rows) + "\n")
    print("   wrote data/qa/reconciliation.md and data/qa/spot_checks.md")
