"""Data-quality checks. Each SQL file in sql/qa returns rows only when a check fails.
Also writes data/qa/unmatched.csv (crosswalk) and prints a short report."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QA_SQL = ROOT / "sql" / "qa"
QA_OUT = ROOT / "data" / "qa"


def run(con) -> bool:
    QA_OUT.mkdir(parents=True, exist_ok=True)
    ok = True
    for f in sorted(QA_SQL.glob("*.sql")):
        rows = con.execute(f.read_text()).df()
        status = "PASS" if rows.empty else "FAIL"
        ok &= rows.empty
        print(f"   [{status}] {f.stem}" + ("" if rows.empty else f"\n{rows.head(10).to_string()}"))
    un = con.execute("""
        SELECT cdn, district_name, district_type, leaid, has_boundary,
               CASE WHEN leaid IS NULL THEN 'no NCES LEAID' WHEN NOT has_boundary THEN 'no boundary polygon' END AS reason
        FROM dim_district WHERE is_isd AND NOT in_analysis ORDER BY cdn""").df()
    un.to_csv(QA_OUT / "unmatched.csv", index=False)
    n_isd, n_ok = (
        con.execute("""SELECT count(*), count(*) FILTER (WHERE in_analysis) FROM dim_district
        WHERE is_isd AND valid_to = (SELECT max(year) FROM stg_peims_summarized)""").fetchone()
    )
    print(
        f"   crosswalk: {n_ok}/{n_isd} ISDs reporting PEIMS in the latest year matched ({n_ok / n_isd:.1%}); "
        f"{len(un)} directory ISDs without a boundary listed in data/qa/unmatched.csv"
    )
    anomalies = con.execute("""SELECT cdn, year, district_name, enrollment, reported_op_per_student_real,
            data_anomaly AS reason FROM mart_district_year WHERE data_anomaly IS NOT NULL ORDER BY year, cdn""").df()
    anomalies.to_csv(QA_OUT / "anomalies.csv", index=False)
    print(f"   district-years removed as data anomalies: {len(anomalies)} (data/qa/anomalies.csv)")
    return ok
