"""NCES EDGE public school locations, 2015-16 through 2024-25 (Texas), for new-campus detection.

A campus is "new" in school year t when its NCES school ID (NCESSCH) first appears in the EDGE file
for year t (t >= 2016-17; 2015-16 is the baseline). Field names are read from each file's header.
TEA AskTED (current directory) provides a Texas-side cross-check via its NCES School ID and
"School Status Date".
"""

from __future__ import annotations

import zipfile

import pandas as pd
import pyogrio

from pipeline.ingest._http import RAW, ROOT, fetch

OUT = ROOT / "data" / "processed"
URL = "https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_{y}.zip"
YEARS = {
    2016: "1516",
    2017: "1617",
    2018: "1718",
    2019: "1819",
    2020: "1920",
    2021: "2021",
    2022: "2122",
    2023: "2223",
    2024: "2324",
    2025: "2425",
}


def _read(year: int, code: str) -> pd.DataFrame:
    """Each zip holds a shapefile, file geodatabase or delimited text (format varies by year).
    Spatial formats are read with pyogrio so field names come from the file itself."""
    z = fetch(URL.format(y=code), RAW / "nces_schools" / f"EDGE_GEOCODE_PUBLICSCH_{code}.zip").path
    xdir = z.parent / code
    if not xdir.exists():
        with zipfile.ZipFile(z) as zf:
            zf.extractall(xdir)
    src = next((p for p in xdir.rglob("*.gdb") if p.is_dir()), None) or next(
        xdir.rglob("*.shp"), None
    )
    if src is None:  # 2024-25 nests the shapefile in a second zip
        for inner in xdir.rglob("*.zip"):
            with zipfile.ZipFile(inner) as zf:
                zf.extractall(inner.with_suffix(""))
        src = next(xdir.rglob("*.shp"), None)
    if src is None:
        raise RuntimeError(f"{code}: no shapefile or geodatabase found")
    layers = [name for name, _ in pyogrio.list_layers(src)]
    layer = next(
        (n for n in layers if "SCH" in n.upper()), layers[0]
    )  # gdb also holds an LEA layer
    df = pyogrio.read_dataframe(src, layer=layer, read_geometry=False)
    df.columns = [c.upper() for c in df.columns]

    def col(prefix):  # field names carry year suffixes in some files (LAT1516, STFIP15, ...)
        return next((c for c in df.columns if c.startswith(prefix)), None)

    df = df[df[col("STFIP")].astype(str).str.zfill(2) == "48"]
    ncessch = df.NCESSCH.astype(str).str.zfill(12)
    lea = col("LEAID")
    # NCESSCH = 7-digit LEAID + 5-digit school number; used where the file has no LEAID column
    # (2015-16). Checked against the LEAID column in every year that has one (tests/test_campuses.py).
    leaid = df[lea].astype(str).str.zfill(7) if lea else ncessch.str[:7]
    loc = col("LOCALE")
    return pd.DataFrame(
        {
            "ncessch": ncessch,
            "leaid": leaid,
            "leaid_from_file": lea is not None,
            "school_name": df.NAME,
            "lat": pd.to_numeric(df[col("LAT")]),
            "lon": pd.to_numeric(df[col("LON")]),
            "year": year,
            "locale_code": df[loc].astype(str) if loc else None,
        }
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for year, code in YEARS.items():
        d = _read(year, code)
        frames.append(d)
        print(f"edge schools {code}: {len(d):,} Texas campuses")
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(OUT / "school_points.parquet", index=False)


if __name__ == "__main__":
    main()
