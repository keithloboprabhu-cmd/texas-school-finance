"""Texas Bond Review Board (BRB) school district debt.

* "Debt Outstanding By Issuance Local By Year" (Texas Open Data Portal, dataset 3qmf-seku; data
  updated 2026-09-10): one row per issuance and state fiscal year (Sept-Aug) with pledge type
  (GO = tax-supported, Rev = revenue-supported, LP), purpose, maturity date, principal / interest /
  total debt service outstanding, ADA and wealth per ADA. ISD rows (governmenttype = 'ISD') only.
* BRB Data Center per-district CSV "cab_cib_debtoutstanding_longitudinal":
  https://data.brb.texas.gov/charts/local/isd/<governmentid>/cab_cib_debtoutstanding_longitudinal.csv
  (columns FiscalYear, CIBPrincipalOutstanding, CIBInterestOutstanding, CABPrincipalOutstanding,
  CABInterestOutstanding), confirmed from the file.
* Crosswalk: BRB `govid` is the CDN in Comptroller format ("037-901-02" -> CDN 037901), so the
  BRB id <-> CDN match is exact; names are compared in tests as a sanity check.

Not available: bond election results. The portal's "Local Debt Bond Election Results" is only a
link to the BRB search site (debtsearch.brb.texas.gov), which is not reachable from the build
environment.
"""

from __future__ import annotations

import time

import pandas as pd
import requests

from pipeline.ingest._http import RAW, ROOT, USER_AGENT, DownloadBlocked, fetch

OUT = ROOT / "data" / "processed"
SOCRATA = "https://data.texas.gov/resource/3qmf-seku.json"
CAB_CIB = (
    "https://data.brb.texas.gov/charts/local/isd/{gid}/cab_cib_debtoutstanding_longitudinal.csv"
)
NUMERIC = [
    "fiscalyear",
    "taxratemo",
    "taxrateis",
    "taxratetotal",
    "taxablevalue",
    "budgetedtotalexpenditures",
    "studentheadcount",
    "adawealth",
    "ada",
    "ada5yrsago",
    "adagrowth",
    "adagrowthpct",
    "totalprincipaloutstanding",
    "totalinterestoutstanding",
    "totaldebtserviceoutstanding",
    "debtperstudentheadcount",
    "debtperada",
]


def ingest_issuance() -> pd.DataFrame:
    rows, offset, page = [], 0, 50_000
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    while True:
        r = s.get(
            SOCRATA,
            params={
                "$where": "governmenttype='ISD'",
                "$limit": page,
                "$offset": offset,
                "$order": "governmentid, fiscalyear, issuancename",
            },
            timeout=120,
        )
        r.raise_for_status()
        batch = r.json()
        rows += batch
        if len(batch) < page:
            break
        offset += page
    df = pd.DataFrame(rows)
    for c in NUMERIC:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    for c in ["closingdate", "maturitydate", "lastprincipalpayment"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["cdn"] = df.govid.str.replace("-", "").str[:6]
    assert df.govid.str.fullmatch(r"\d{3}-\d{3}-\d{2}").all(), "unexpected BRB govid format"
    df.to_parquet(OUT / "brb_issuance.parquet", index=False)
    print(
        f"brb issuance: {len(df):,} ISD issuance-years, FY {df.fiscalyear.min():.0f}-{df.fiscalyear.max():.0f}, "
        f"{df.governmentid.nunique()} issuers"
    )
    return df


def ingest_cab_cib(issuers: pd.DataFrame) -> pd.DataFrame:
    frames, missing = [], []
    for gid, cdn in issuers[["governmentid", "cdn"]].drop_duplicates().itertuples(index=False):
        dest = RAW / "brb_cab_cib" / f"{gid}.csv"
        try:
            path = fetch(CAB_CIB.format(gid=gid), dest, retries=2, timeout=60).path
        except DownloadBlocked:
            missing.append(gid)
            continue
        if not dest.exists() or dest.stat().st_size == 0:
            continue
        df = pd.read_csv(path)
        if "FiscalYear" not in df.columns:
            missing.append(gid)
            continue
        frames.append(df.assign(governmentid=str(gid), cdn=cdn))
        time.sleep(0.15)  # polite pacing
    out = pd.concat(frames, ignore_index=True).rename(columns=str.lower)
    out.to_parquet(OUT / "brb_cab_cib.parquet", index=False)
    print(f"brb cab/cib: {out.governmentid.nunique()} districts; {len(missing)} without a CSV")
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    iss = ingest_issuance()
    ingest_cab_cib(iss[iss.fiscalyear == iss.fiscalyear.max()])


if __name__ == "__main__":
    main()
