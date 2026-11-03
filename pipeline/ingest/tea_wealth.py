"""Property wealth, property mix and tax rates.

* TEA "PTAD Tax Final" files (Comptroller certified values, posted by TEA), tax years 2010-2025.
  Column used: "<tax year> value assigned (used for school funding)" -> `value_assigned`.
  Tax year 2009's link on TEA's page returns "Page not found", so the series starts in 2010.
* Comptroller PVS final "ISD Worksheet Export Summary", tax years 2022-2025: property value by
  PTAD category (assigned values, "ASGN <cat>"). Used only for property mix (mineral share etc.).
  Category labels confirmed from the Comptroller statewide worksheet (e.g. "G - ALL MINERALS").
* TEA adopted M&O and I&S tax rates, 2005-06 to the latest school year (one Excel file).
Source page: https://tea.texas.gov/about-tea/state-funding/additional-finance-resources/school-district-property-values-and-tax-rates
"""

from __future__ import annotations

import re
import warnings

import pandas as pd

from pipeline.ingest._http import RAW, ROOT, fetch

OUT = ROOT / "data" / "processed"
_B = "https://tea.texas.gov"
_A = f"{_B}/about-tea/state-funding/additional-finance-resources"
_L = f"{_B}/WorkArea/linkit.aspx?LinkIdentifier=id&ItemID="
CPTD_URLS = {
    2025: f"{_A}/cptd-2025-final-data.xlsx",
    2024: f"{_A}/cptd-2024-final.xlsx",
    2023: f"{_A}/cptd-2023-final.xlsx",
    2022: f"{_A}/cptd-2022-final.xlsx",
    2021: f"{_A}/cptd-2021-final.xlsx",
    2020: f"{_A}/cptd-2020-final.xlsx",
    2019: f"{_B}/sites/default/files/cptd-2019-final.xlsx",
    2018: f"{_B}/sites/default/files/cptd_2018_final.xls",
    2017: f"{_B}/sites/default/files/cptd_2017_final.xlsx",
    2016: f"{_B}/sites/default/files/cptd_2016_final.xlsx",
    2015: f"{_B}/sites/default/files/cptd_2015_final.xlsx",
    2014: f"{_L}25769825216",
    2013: f"{_L}25769814550",
    2012: f"{_L}25769809873",
    2011: f"{_L}2147508387",
    2010: f"{_L}2147508057",
}
TAX_RATES_URL = f"{_A}/school-district-adopted-tax-rates-1.xlsx"
PVS_URL = "https://comptroller.texas.gov/taxes/property-tax/docs/{y}-final-isd-worksheet-export-summary.xlsx"
PVS_YEARS = [2022, 2023, 2024, 2025]
# PTAD property categories (labels from the Comptroller PVS statewide summary worksheet)
PVS_CATEGORIES = {
    "A": "single_family_residential",
    "B": "multifamily_residential",
    "C1": "vacant_lots",
    "C2": "colonia_lots",
    "D1": "qualified_ag_land",
    "D2": "farm_ranch_improvements",
    "E": "rural_non_ag",
    "F1": "commercial_real",
    "F2": "industrial_real",
    "G": "minerals",
    "J": "utilities",
    "L1": "commercial_personal",
    "L2": "industrial_personal",
    "M": "mobile_homes",
    "N": "intangible_personal",
    "O": "residential_inventory",
    "S": "special_inventory",
}


def _read_any_excel(path, **kw) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        head = path.read_bytes()[:8]
        engine = "xlrd" if head.startswith(b"\xd0\xcf\x11\xe0") else "openpyxl"
        return pd.read_excel(path, engine=engine, **kw)


def _cdn(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(6)


def ingest_cptd() -> pd.DataFrame:
    frames = []
    for ty, url in sorted(CPTD_URLS.items()):
        path = fetch(url, RAW / "tea_cptd" / f"cptd_{ty}.bin").path
        raw = _read_any_excel(path, header=None, dtype=object)
        # header text sits in the first two rows; combine them per column
        labels = [
            " ".join(str(v) for v in raw.iloc[:2, j] if isinstance(v, str))
            for j in range(raw.shape[1])
        ]

        def find(pattern: str, labels=labels, ty=ty) -> int:
            hits = [j for j, lab in enumerate(labels) if re.search(pattern, lab, re.I)]
            if len(hits) != 1:
                raise RuntimeError(f"tax year {ty}: pattern {pattern!r} matched {hits}")
            return hits[0]

        cols = {
            "t1": find(r"(^|\s)T1 ="),
            "t2": find(r"(^|\s)T2 ="),
            "value_assigned": find(r"value assigned \(used for school funding\)"),
        }
        # e.g. "Final Tax Year 2016 values (Used for School Funding in school-year 2017-18)"
        m = re.search(r"school[- ]year (\d{4})-(\d{2,4})", " ".join(labels), re.I)
        funded_sy_end = (int(m.group(1)) + 1) if m else None
        body = raw[raw[0].astype(str).str.fullmatch(r"\d{4,6}(\.0)?")]
        df = pd.DataFrame(
            {
                "cdn": _cdn(body[0]),
                "tax_year": ty,
                "district_name": body[1].astype(str).str.strip(),
                **{k: pd.to_numeric(body[j], errors="coerce") for k, j in cols.items()},
            }
        )
        frames.append(df)
        print(f"cptd {ty}: {len(df):,} districts, used for school year ending {funded_sy_end}")
    out = pd.concat(frames, ignore_index=True)
    assert not out.duplicated(["cdn", "tax_year"]).any()
    out.to_parquet(OUT / "property_values.parquet", index=False)
    return out


def ingest_pvs_mix() -> pd.DataFrame:
    frames = []
    for ty in PVS_YEARS:
        path = fetch(
            PVS_URL.format(y=ty), RAW / "comptroller_pvs" / f"{ty}f_isd_worksheet_summary.xlsx"
        ).path
        df = _read_any_excel(path, header=2, dtype=str)
        # "TU ID" is the CDN with dashes plus a 2-digit suffix: "001-902-02" -> "001902"
        tu = df["TU ID"].str.fullmatch(r"\d{3}-\d{3}-\d{2}")
        df = df[tu]
        rec = pd.DataFrame({"cdn": df["TU ID"].str[:7].str.replace("-", ""), "tax_year": ty})
        for code, name in PVS_CATEGORIES.items():
            rec[f"value_{name}"] = (
                pd.to_numeric(df[f"ASGN {code}"], errors="coerce").fillna(0).values
            )
        rec["value_category_total"] = pd.to_numeric(df["ASGN CATG TOT"]).values
        rec["value_t2_pvs"] = pd.to_numeric(df["ASGN T2"]).values
        frames.append(rec)
        print(f"pvs {ty}: {len(rec):,} districts")
    out = pd.concat(frames, ignore_index=True)
    assert not out.duplicated(["cdn", "tax_year"]).any()
    out.to_parquet(OUT / "property_mix.parquet", index=False)
    return out


def ingest_tax_rates() -> pd.DataFrame:
    path = fetch(
        TAX_RATES_URL, RAW / "tea_tax_rates" / "school_district_adopted_tax_rates.xlsx"
    ).path
    raw = _read_any_excel(path, header=0, dtype=object)
    raw = raw[raw.iloc[:, 0].astype(str).str.fullmatch(r"\d{4,6}(\.0)?")]
    long = []
    for col in raw.columns[2:]:
        m = re.search(r"(\d{4})-(\d{4})\s+(M&O|I&S)", str(col))
        if not m:
            continue
        long.append(
            pd.DataFrame(
                {
                    "cdn": _cdn(raw.iloc[:, 0]),
                    "year": int(m.group(2)),
                    "rate_type": m.group(3),
                    "rate": pd.to_numeric(raw[col], errors="coerce"),
                }
            )
        )
    df = (
        pd.concat(long)
        .pivot_table(index=["cdn", "year"], columns="rate_type", values="rate")
        .reset_index()
    )
    df = df.rename(columns={"M&O": "mo_rate", "I&S": "is_rate"})
    df.columns.name = None
    df.to_parquet(OUT / "tax_rates.parquet", index=False)
    print(f"tax rates: {len(df):,} district-years, {df.year.min()}-{df.year.max()}")
    return df


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ingest_cptd()
    ingest_pvs_mix()
    ingest_tax_rates()


if __name__ == "__main__":
    main()
