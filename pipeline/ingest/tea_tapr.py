"""TEA Texas Academic Performance Reports (TAPR), district level, Advanced Download "PROF"
(Staff, Student, and Annual Graduates), 2023-24 (the 2024-25 TAPR was not yet published).

Field codes confirmed in TEA's TAPR data dictionary (Basic Download/datadict.pdf):
  DPETALLC total students, DPETECOC economically disadvantaged, DPETLEPC emergent bilingual/EL,
  DPETSPEC special education (all counts). "*" marks masked values; masked or non-numeric cells
  are treated as missing, never zero.
"""

from __future__ import annotations

import pandas as pd

from pipeline.ingest._http import RAW, ROOT, fetch

OUT = ROOT / "data" / "processed"
BROKER = "https://rptsvr1.tea.texas.gov/cgi/sas/broker"
YEARS = {2024: "2024/tapr/Advanced Download/getdata_2024.sas"}
FIELDS = {
    "DPETALLC": "tapr_students",
    "DPETECOC": "econ_disadv",
    "DPETLEPC": "english_learners",
    "DPETSPEC": "special_ed",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for year, prog in YEARS.items():
        params = {
            "_service": "marykay",
            "_program": "perfrept.perfmast.sas",
            "_debug": "0",
            "prgopt": prog,
            "ccyy": str(year),
            "sumlev": "D",
            "setpick": "PROF",
        }
        path = fetch(
            BROKER, RAW / "tea_tapr" / f"tapr_{year}_district_prof.csv", params=params
        ).path
        d = pd.read_csv(path, dtype=str)
        out = pd.DataFrame({"cdn": d.DISTRICT.str.lstrip("'").str.zfill(6), "tapr_year": year})
        for src, dst in FIELDS.items():
            out[dst] = pd.to_numeric(d[src], errors="coerce").where(lambda s: s >= 0).values
        for c in ["econ_disadv", "english_learners", "special_ed"]:
            out[f"{c}_pct"] = out[c] / out.tapr_students
        frames.append(out)
        print(f"tapr {year}: {len(out):,} districts")
    pd.concat(frames).to_parquet(OUT / "tapr.parquet", index=False)


if __name__ == "__main__":
    main()
