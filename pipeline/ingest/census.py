"""Census SAIPE (child poverty) and ACS 5-year (income, home value, population) by school district.

The Census Data API rejected the project's key ("Invalid Key", probably not yet activated) and
now refuses keyless requests ("missing_key"), so this module reads Census's own published flat files:

* SAIPE school district estimates, 2024: https://www2.census.gov/programs-surveys/saipe/datasets/2024/2024-school-districts/ussd24.xls
  Columns (header row of the file): state, distid (5-digit), name, rpop5_17v_24 (relevant
  population age 5-17), saepov5_17rv_24 (relevant age 5-17 in families in poverty). These
  match the API variables SAEPOV5_17V_PT and SAEPOV5_17RV_PT.
* ACS 2020-2024 5-year table-based summary files, tables B19013 (median household income),
  B25077 (median home value) and B01003 (total population):
  https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/
  School districts are summary levels 950 (elementary), 960 (secondary) and 970 (unified);
  GEO_ID is e.g. 9700000US4823640 and its last 7 digits are the NCES LEAID / Census GEOID.
"""

from __future__ import annotations

import pandas as pd

from pipeline.ingest._http import RAW, ROOT, fetch

OUT = ROOT / "data" / "processed"
SAIPE_URL = (
    "https://www2.census.gov/programs-surveys/saipe/datasets/2024/2024-school-districts/ussd24.xls"
)
ACS_URL = "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-{t}.dat"
ACS_TABLES = {
    "b19013": {
        "B19013_E001": "median_household_income",
        "B19013_M001": "median_household_income_moe",
    },
    "b25077": {"B25077_E001": "median_home_value"},
    "b01003": {"B01003_E001": "total_population"},
}
SUMLEVEL_TYPE = {"950": "elementary", "960": "secondary", "970": "unified"}


def ingest_saipe() -> pd.DataFrame:
    path = fetch(SAIPE_URL, RAW / "census_saipe" / "ussd24.xls").path
    df = pd.read_excel(path, dtype=str)
    df = df[df["state"] == "48"]
    out = pd.DataFrame(
        {
            "geoid": "48" + df["distid"].str.zfill(5),
            "saipe_name": df["name"],
            "saipe_year": 2024,
            "pop_5_17": pd.to_numeric(df["rpop5_17v_24"]),
            "poverty_5_17": pd.to_numeric(df["saepov5_17rv_24"]),
        }
    )
    out = out[out.geoid != "4899999"]  # Census "remainder of state" pseudo-district
    out["child_poverty_rate"] = out.poverty_5_17 / out.pop_5_17
    assert not out.geoid.duplicated().any()
    out.to_parquet(OUT / "saipe.parquet", index=False)
    print(f"saipe 2024: {len(out):,} Texas districts")
    return out


def ingest_acs() -> pd.DataFrame:
    merged = None
    for table, cols in ACS_TABLES.items():
        path = fetch(ACS_URL.format(t=table), RAW / "census_acs" / f"acsdt5y2024-{table}.dat").path
        df = pd.read_csv(path, sep="|", dtype=str)
        df = df[df.GEO_ID.str.match(r"^9[567]00000US48\d{5}$")]
        df = df[~df.GEO_ID.str.endswith("99999")]
        part = pd.DataFrame(
            {"geoid": df.GEO_ID.str[-7:], "sd_type": df.GEO_ID.str[:3].map(SUMLEVEL_TYPE)}
        )
        for src, dst in cols.items():
            # ACS uses negative sentinel values for suppressed / not-computable estimates
            v = pd.to_numeric(df[src], errors="coerce")
            part[dst] = v.where(v >= 0).values
        merged = (
            part if merged is None else merged.merge(part, on=["geoid", "sd_type"], how="outer")
        )
    merged["acs_vintage"] = "2020-2024 ACS 5-year"
    assert not merged.geoid.duplicated().any()
    merged.to_parquet(OUT / "acs.parquet", index=False)
    print(
        f"acs 2020-2024: {len(merged):,} Texas districts ({merged.sd_type.value_counts().to_dict()})"
    )
    return merged


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ingest_saipe()
    ingest_acs()


if __name__ == "__main__":
    main()
