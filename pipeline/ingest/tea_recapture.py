"""Recapture (excess local revenue) from TEA's Excess Local Revenue page.

https://tea.texas.gov/about-tea/state-funding/excess-local-revenue

* "1993-1994 to 2026-2027 Recapture Paid by District" (Excel): per district and fiscal year,
  "<YYYY> Total Recapture" (dollars) and "Chapter 41/49 Designation <YYYY>" ("YES").
  Footnotes in the file: ** 2026 amounts are near-final, *** 2027 amounts are preliminary.
* Excess Local Revenue district lists (Excel), 2025-26 and 2026-27: TEA's July notification
  lists with entitlement, property value, local fund assignment and excess revenue columns.
  TEA notes that districts on the list do not necessarily owe recapture.
* The 2025-26 list is also parsed from TEA's PDF and its row count is checked against the
  PDF's own "COUNT:" line and against the Excel version.
"""

from __future__ import annotations

import re

import pandas as pd
import pdfplumber

from pipeline.ingest._http import RAW, ROOT, fetch

OUT = ROOT / "data" / "processed"
_E = "https://tea.texas.gov/about-tea/state-funding/excess-local-revenue"
PAID_URL = "https://tea.texas.gov/about-tea/state-funding/state-funding-reports-and-data/recapture-paid-by-district.xlsx"
ELR_XLSX = {
    2026: f"{_E}/2025-2026-excess-local-revenue-districts.xlsx",
    2027: f"{_E}/2026-2027-excess-local-revenue-districts.xlsx",
}
ELR_PDF_2026 = f"{_E}/2025-2026-excess-local-revenue-districts.pdf"
D = RAW / "tea_recapture"

ELR_COLUMNS = {  # header text in TEA's file (first 40 chars, case-insensitive) -> our name
    "cdn": "cdn",
    "district name": "district_name",
    "estimated tier one entitlement": "tier_one_entitlement",
    "estimated asf allotment": "asf_allotment",
    "estimated 20": "district_property_value",  # "Estimated 2025 State Certified District Property Value (DPV)"
    "estimated tax year": "tier_one_tax_rate",
    "estimated local fund assignment": "local_fund_assignment",
    "estimated tier one excess revenue": "tier_one_excess_revenue",
    "estimated compressed m&o tax collections": "compressed_mo_collections",
    "adjustment for revenue below entitlement": "adjustment_below_entitlement",
    "tier one excess local revenue after adju": "tier_one_excess_after_adjustment",
    "tier two guaranteed yield": "tier_two_guaranteed_yield",
    "chapter 48 wada": "wada",
    "estimated chapter 48 local yield per pen": "local_yield_per_penny_per_wada",
    "estimated tier two level two entitlement": "tier_two_l2_entitlement",
    "estimated tier two level two local reven": "tier_two_l2_local_revenue",
    "estimated tier two level two excess reve": "tier_two_l2_excess_revenue",
}


def _money(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[$,\s]", "", regex=True), errors="coerce")


def ingest_paid() -> pd.DataFrame:
    path = fetch(PAID_URL, D / "recapture_paid_by_district.xlsx").path
    x = pd.read_excel(path, header=None, dtype=object)
    header = [str(v) for v in x.iloc[0]]
    body = x.iloc[1:][x.iloc[1:, 0].astype(str).str.fullmatch(r"\d{4,6}")]
    rows = []
    for j, label in enumerate(header):
        m = re.search(r"(\d{4})\s+Total Recapture", label)
        if not m:
            continue
        fy = int(m.group(1))
        des = next((k for k, h in enumerate(header) if re.search(rf"Designation {fy}\b", h)), None)
        status = (
            "preliminary"
            if label.startswith("***")
            else "near-final"
            if label.startswith("**")
            else "final"
        )
        rows.append(
            pd.DataFrame(
                {
                    "cdn": body[0].astype(str).str.zfill(6),
                    "year": fy,
                    "recapture_paid": _money(body[j]),
                    "designated": body[des].astype(str).str.upper().eq("YES")
                    if des is not None
                    else pd.NA,
                    "amount_status": status,
                }
            )
        )
    df = pd.concat(rows, ignore_index=True)
    df = df[df.recapture_paid.notna() | df.designated.fillna(False).astype(bool)]
    assert not df.duplicated(["cdn", "year"]).any()
    df.to_parquet(OUT / "recapture_paid.parquet", index=False)
    print(f"recapture paid: {len(df):,} district-years, {df.year.min()}-{df.year.max()}")
    return df


def ingest_elr_lists() -> pd.DataFrame:
    frames = []
    for year, url in ELR_XLSX.items():
        path = fetch(url, D / f"elr_{year}.xlsx").path
        x = pd.read_excel(path, header=None, dtype=object)
        h = x.index[x[0].astype(str).str.strip().str.upper().eq("CDN")][0]
        labels = [re.sub(r"\s+", " ", str(v)).strip().lower() for v in x.iloc[h]]
        rename = {}
        for j, lab in enumerate(labels):
            if "chapter 48 wada" in lab:  # must win over the "estimated 20" prefix
                key = "chapter 48 wada"
            else:
                key = next((k for k in ELR_COLUMNS if lab.startswith(k)), None)
            if key is None:
                raise RuntimeError(f"ELR {year}: unrecognised column {lab!r}")
            rename[j] = ELR_COLUMNS[key]
        body = x.iloc[h + 1 :].rename(columns=rename)
        assert body.columns.is_unique, f"ELR {year}: duplicate column mapping {list(body.columns)}"
        body = body[pd.to_numeric(body["cdn"], errors="coerce").notna()].copy()
        body["cdn"] = body["cdn"].astype(int).astype(str).str.zfill(6)
        for c in body.columns[2:]:
            body[c] = pd.to_numeric(body[c], errors="coerce")
        body.insert(1, "year", year)
        frames.append(body)
        print(f"ELR list {year - 1}-{year}: {len(body)} districts")
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(OUT / "elr_lists.parquet", index=False)
    _check_pdf_count(df[df.year == 2026])
    return df


def _check_pdf_count(xlsx_2026: pd.DataFrame) -> None:
    path = fetch(ELR_PDF_2026, D / "elr_2026.pdf").path
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    declared = int(re.search(r"COUNT:\s*(\d+)", text).group(1))
    parsed = set(re.findall(r"^\s*(\d{6})\s+\S", text, re.M))
    assert len(parsed) == declared, f"PDF rows {len(parsed)} != COUNT {declared}"
    assert parsed == set(xlsx_2026.cdn), "PDF and Excel 2025-26 lists differ"
    print(f"ELR 2025-26 PDF: COUNT {declared} = parsed rows = Excel rows")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ingest_paid()
    ingest_elr_lists()


if __name__ == "__main__":
    main()
