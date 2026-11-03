"""TEA PEIMS actual financial data.

Two inputs, both from TEA's PEIMS Financial Data Downloads pages:

1. Summarized actuals, 2008-09 through 2024-25 (one Excel, sheet DATAMART): one row per
   district (including charters) and year, with TEA's own totals ("GEN FUNDS-" = general fund,
   "ALL FUNDS-" = all funds). Used for TEA's published totals, revenue mix and fall enrollment.
2. Single-file district actuals, one CSV per year (DISTRICT, FUND, FUNDYEAR, FUNCTION, OBJECT,
   FIN_UNIT, [PROGRAM_INTENT], ACTAMT, DTUPDATE). Aggregated here to
   (cdn, year, fund, function, object_series) so the pipeline can apply exclusions by code.

Conventions confirmed from the files themselves:
  * YEAR in the summarized file is the school year's ending year: "2025" = 2024-25 (the
    single-file page labels the matching download "District 2024-2025 Financial Actual Data").
  * DISTRICT NUMBER in the summarized file is "'001902" (leading apostrophe); stripped to the
    6-digit CDN string. The single file's DISTRICT is already 6 digits.
  * Single files cover non-charter districts only (1,019 districts in 2024-25); charters are in
    separate files that this project does not need (charters are excluded from the analysis).
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.ingest._http import RAW, ROOT, fetch

SUMMARIZED_URL = "https://tea.texas.gov/media/423296"
DICTIONARY_URL = "https://tea.texas.gov/WorkArea/linkit.aspx?LinkIdentifier=id&ItemID=2147494868"
_TEA = "https://tea.texas.gov"
_RPT = "https://rptsvr1.tea.texas.gov/school.finance/forecasting/downloads/Actual_Singlefile"
# District actual single files, keyed by school-year ending year. Links copied from
# https://tea.texas.gov/about-tea/state-funding/state-funding-reports-and-data/peims-single-file-financial-data-downloads
SINGLE_FILE_URLS = {
    2025: f"{_TEA}/media/423221",
    2024: f"{_TEA}/data-reports/financial-reports/school-finance-reports-and-data/actget2024.zip",
    2023: f"{_TEA}/data-reports/financial-reports/school-finance-reports-and-data/actget2023.zip",
    2022: f"{_TEA}/about-tea/state-funding/state-funding-reports-and-data/actget2022.zip",
    2021: f"{_TEA}/about-tea/state-funding/state-funding-reports-and-data/actget2021.zip",
    2020: f"{_TEA}/sites/default/files/actget2020.zip",
    2019: f"{_TEA}/sites/default/files/ACTget2019.zip",
    2018: f"{_TEA}/sites/default/files/ACTget2018.zip",
    2017: f"{_TEA}/sites/default/files/ACTget2017.zip",
    2016: f"{_TEA}/sites/default/files/ACTget2016.zip",
    2015: f"{_TEA}/WorkArea/linkit.aspx?LinkIdentifier=id&ItemID=25769825543",
    2014: f"{_TEA}/WorkArea/linkit.aspx?LinkIdentifier=id&ItemID=25769820605",
    2013: f"{_TEA}/WorkArea/linkit.aspx?LinkIdentifier=id&ItemID=25769810372",
    2012: f"{_TEA}/data-reports/financial-reports/school-finance-reports-and-data/district-final-actual-data-2011-12.zip",
    2011: f"{_RPT}/2011Actual.zip",
    2010: f"{_RPT}/2010Actual.zip",
    2009: f"{_RPT}/2009Actual.zip",
}

RAW_DIR = RAW / "tea_peims"
SINGLE_DIR = RAW / "tea_peims_single"
OUT = ROOT / "data" / "processed"


def ingest_summarized() -> Path:
    src = fetch(SUMMARIZED_URL, RAW_DIR / "peims_actuals_summarized_2009_2025.xlsx").path
    fetch(DICTIONARY_URL, RAW_DIR / "peims_financial_data_dictionary.pdf")
    df = pd.read_excel(src, sheet_name="DATAMART", dtype=str)
    df.insert(0, "cdn", df.pop("DISTRICT NUMBER").str.lstrip("'").str.zfill(6))
    assert df["cdn"].str.fullmatch(r"\d{6}").all(), "unexpected DISTRICT NUMBER format"
    df.insert(1, "year", df.pop("YEAR").astype(int))
    df = df.rename(columns={"DISTRICT NAME": "district_name"})
    for c in df.columns[3:]:
        df[c] = pd.to_numeric(df[c])
    out = OUT / "peims_summarized.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"peims_summarized: {len(df):,} rows, years {df.year.min()}-{df.year.max()}")
    return out


def ingest_single_year(year: int, keep_csv: bool = False) -> Path:
    out = OUT / "peims_actuals" / f"year={year}.parquet"
    if out.exists():
        return out
    url = SINGLE_FILE_URLS[year]
    zpath = fetch(url, SINGLE_DIR / f"district_actual_{year}.zip").path
    xdir = SINGLE_DIR / f"y{year}"
    with zipfile.ZipFile(zpath) as z:
        z.extractall(xdir)
    csvs = [p for p in xdir.rglob("*") if p.suffix.lower() in {".csv", ".txt", ".dat"}]
    if len(csvs) != 1:
        raise RuntimeError(f"{year}: expected one CSV in {zpath.name}, found {csvs}")
    con = duckdb.connect()
    src = csvs[0].as_posix().replace("'", "''")
    cols = {
        c[0].upper(): c[0]
        for c in con.execute(
            f"DESCRIBE SELECT * FROM read_csv('{src}', all_varchar=true, header=true)"
        ).fetchall()
    }
    need = ["DISTRICT", "FUND", "FUNCTION", "OBJECT", "ACTAMT"]
    missing = [n for n in need if n not in cols]
    if missing:
        raise RuntimeError(f"{year}: columns {missing} not found; have {list(cols)}")
    out.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        COPY (
          SELECT lpad(trim("{cols["DISTRICT"]}"), 6, '0')    AS cdn,
                 {year}::SMALLINT                             AS year,
                 lpad(trim("{cols["FUND"]}"), 3, '0')         AS fund,
                 lpad(trim("{cols["FUNCTION"]}"), 2, '0')     AS function,
                 substr(lpad(trim("{cols["OBJECT"]}"), 4, '0'), 1, 2) || '00' AS object_series,
                 sum(trim("{cols["ACTAMT"]}")::DOUBLE)        AS amount,
                 count(*)::INTEGER                            AS n_rows
          FROM read_csv('{src}', all_varchar=true, header=true)
          GROUP BY ALL
        ) TO '{out.as_posix()}' (FORMAT parquet)
    """)
    n = con.execute(f"SELECT count(*), count(DISTINCT cdn) FROM '{out.as_posix()}'").fetchone()
    print(f"peims_actuals {year}: {n[0]:,} aggregated rows, {n[1]:,} districts")
    if not keep_csv:
        shutil.rmtree(xdir)
    return out


def main(years: list[int] | None = None) -> None:
    ingest_summarized()
    for y in years or sorted(SINGLE_FILE_URLS):
        ingest_single_year(y)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or None)
