"""Definitions: the code-based operating-spending rule must reproduce TEA's own totals."""

from conftest import PROCESSED, needs

ACTUALS = PROCESSED / "peims_actuals"
SUMMARIZED = PROCESSED / "peims_summarized.parquet"


def test_reference_tables_cover_all_codes(ref_con):
    fns = {r[0] for r in ref_con.execute("SELECT function FROM ref_function_groups").fetchall()}
    # Functions excluded from operating spending (Section 4 of the spec), cited in the SQL file
    for code in ["71", "81", "91", "93", "97", "99"]:
        assert code in fns
        assert not ref_con.execute(
            "SELECT in_operating FROM ref_function_groups WHERE function = ?", [code]
        ).fetchone()[0]
    assert ref_con.execute("SELECT fund_group('699')").fetchone()[0] == "capital_projects"
    assert ref_con.execute("SELECT fund_group('199')").fetchone()[0] == "general"
    assert ref_con.execute("SELECT fund_group('315')").fetchone()[0] == "ssa_fiscal_agent_federal"


@needs(ACTUALS)
def test_operating_rule_matches_tea_totals(ref_con):
    ref_con.execute(f"CREATE VIEW a AS SELECT * FROM read_parquet('{ACTUALS}/*.parquet')")
    ref_con.execute(f"CREATE VIEW s AS SELECT * FROM read_parquet('{SUMMARIZED}')")
    rows = ref_con.execute("""
        WITH op AS (
          SELECT a.cdn, a.year, sum(amount) v
          FROM a JOIN ref_function_groups g USING (function)
                 JOIN ref_object_groups o USING (object_series)
          WHERE g.in_operating AND o.is_operating_object
            AND fund_group(a.fund) <> 'capital_projects'
          GROUP BY ALL)
        SELECT s.year,
               avg((abs(coalesce(op.v, 0) - s."ALL FUNDS-TOTAL OPER EXPENDITURES FOR TD") <= 1)::INT),
               sum(op.v) / sum(s."ALL FUNDS-TOTAL OPER EXPENDITURES FOR TD")
        FROM s LEFT JOIN op USING (cdn, year)
        WHERE s.cdn IN (SELECT DISTINCT cdn FROM a WHERE a.year = s.year)
        GROUP BY 1
    """).fetchall()
    assert len(rows) == 17
    for year, exact_share, state_ratio in rows:
        assert exact_share >= 0.98, f"{year}: only {exact_share:.1%} of districts match exactly"
        assert abs(state_ratio - 1) < 0.001, f"{year}: statewide total off by {state_ratio - 1:.3%}"
