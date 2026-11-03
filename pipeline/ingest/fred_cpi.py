"""CPI-U (FRED series CPIAUCSL, seasonally adjusted, 1982-84=100) for inflation adjustment.

Uses the FRED API when FRED_API_KEY is set (in the environment or .env); otherwise falls back to
the committed snapshot data/ref/cpi_cpiaucsl_monthly.csv. School-year averages use July through
June (e.g. school year 2024-25 = July 2024 - June 2025).
"""

from __future__ import annotations

import os

import pandas as pd
import requests

from pipeline.ingest._http import ROOT, USER_AGENT

SNAPSHOT = ROOT / "data" / "ref" / "cpi_cpiaucsl_monthly.csv"
OUT = ROOT / "data" / "processed"


def _api_key() -> str | None:
    if os.environ.get("FRED_API_KEY"):
        return os.environ["FRED_API_KEY"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FRED_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def fetch_monthly() -> pd.DataFrame:
    key = _api_key()
    if key:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": "CPIAUCSL",
                "api_key": key,
                "file_type": "json",
                "observation_start": "2000-01-01",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        r.raise_for_status()
        obs = pd.DataFrame(r.json()["observations"])[["date", "value"]]
        obs["value"] = pd.to_numeric(obs["value"], errors="coerce")
        obs = obs.dropna()
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        obs.to_csv(SNAPSHOT, index=False)
        print(f"CPI from FRED API: {obs.date.min()} to {obs.date.max()} (snapshot updated)")
        return obs
    obs = pd.read_csv(SNAPSHOT)
    print(f"CPI from committed snapshot: {obs.date.min()} to {obs.date.max()}")
    return obs


def school_year_cpi(obs: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(obs["date"])
    sy = d.dt.year + (d.dt.month >= 7).astype(int)  # July starts the next school year
    df = (
        obs.assign(year=sy)
        .groupby("year")
        .agg(cpi=("value", "mean"), months=("value", "size"))
        .reset_index()
    )
    return df[df.months == 12].drop(columns="months")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sy = school_year_cpi(fetch_monthly())
    sy.to_parquet(OUT / "cpi_school_year.parquet", index=False)
    print(f"school-year CPI: {sy.year.min()}-{sy.year.max()}")


if __name__ == "__main__":
    main()
