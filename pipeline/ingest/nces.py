"""NCES and TEA directory inputs: district boundaries, LEA directory, LEA geocodes, AskTED.

* NCES EDGE School District Composites SY 2024-25 (TL 2025), filtered to STATEFP 48.
  ID field GEOID = 7-digit LEAID (e.g. 4818120). Elementary (ELSDLEA), secondary (SCSDLEA) and
  unified (UNSDLEA) districts are separate rows.
* NCES CCD LEA directory 2023-24 (ccd_lea_029_2324_w_1a_073124): ST_LEAID is "TX-" + 6-digit
  CDN (confirmed from the file), LEAID is the 7-digit NCES ID.
* NCES EDGE LEA geocodes 2024-25: county, CBSA and NCES locale per LEAID. The TXT file has no
  header; field names come from the matching shapefile's DBF.
* TEA AskTED "Download School and District File" (form post): district number, NCES district
  ID, ESC region, district type and every campus with its NCES school ID and status date.
"""

from __future__ import annotations

import re
import zipfile

import geopandas as gpd
import pandas as pd
import requests

from pipeline.ingest._http import RAW, ROOT, USER_AGENT, fetch

OUT = ROOT / "data" / "processed"
BOUNDARIES_URL = "https://nces.ed.gov/programs/edge/data/EDGE_SCHOOLDISTRICT_TL25_SY2425.zip"
CCD_LEA_URL = "https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2324_w_1a_073124.zip"
EDGE_LEA_URL = "https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICLEA_2425.zip"
ASKTED_URL = "https://tealprod.tea.state.tx.us/Tea.AskTed.Web/Forms/DownloadFile.aspx"
EDGE_LEA_FIELDS = [
    "LEAID",
    "NAME",
    "OPSTFIPS",
    "STREET",
    "CITY",
    "STATE",
    "ZIP",
    "STFIP",
    "CNTY",
    "NMCNTY",
    "LAT",
    "LON",
    "CBSA",
    "NMCBSA",
    "CBSATYPE",
    "CSA",
    "NMCSA",
    "CD",
    "SLDL",
    "SLDU",
    "SCHOOLYEAR",
    "LOCALE",
    "PCT_CITY11",
    "PCT_CITY12",
    "PCT_CITY13",
    "PCT_SUB21",
    "PCT_SUB22",
    "PCT_SUB23",
    "PCT_TOWN31",
    "PCT_TOWN32",
    "PCT_TOWN33",
    "PCTRURAL41",
    "PCTRURAL42",
    "PCTRURAL43",
]


def _unzip(path, dest):
    with zipfile.ZipFile(path) as z:
        z.extractall(dest)
    return dest


def ingest_boundaries() -> gpd.GeoDataFrame:
    z = fetch(BOUNDARIES_URL, RAW / "nces_boundaries" / "EDGE_SCHOOLDISTRICT_TL25_SY2425.zip").path
    shp = next(_unzip(z, z.parent / "x").rglob("*.shp"))
    g = gpd.read_file(shp, where="STATEFP = '48'")
    g["sd_type"] = (
        g.UNSDLEA.notna()
        .map({True: "unified"})
        .fillna(g.ELSDLEA.notna().map({True: "elementary"}))
        .fillna(g.SCSDLEA.notna().map({True: "secondary"}))
    )
    g = g[
        [
            "GEOID",
            "NAME",
            "sd_type",
            "LOGRADE",
            "HIGRADE",
            "ALAND",
            "AWATER",
            "INTPTLAT",
            "INTPTLON",
            "geometry",
        ]
    ]
    g = g.rename(
        columns={"GEOID": "geoid", "NAME": "boundary_name", "ALAND": "aland", "AWATER": "awater"}
    )
    g["int_lat"] = pd.to_numeric(g.pop("INTPTLAT"))
    g["int_lon"] = pd.to_numeric(g.pop("INTPTLON"))
    g.to_parquet(OUT / "boundaries.parquet", index=False)
    print(f"boundaries: {len(g):,} Texas polygons {g.sd_type.value_counts().to_dict()}")
    return g


def ingest_ccd_lea() -> pd.DataFrame:
    z = fetch(CCD_LEA_URL, RAW / "nces_ccd_lea" / "ccd_lea_029_2324_w_1a_073124.zip").path
    csv = next(_unzip(z, z.parent).glob("*.csv"))
    d = pd.read_csv(csv, dtype=str)
    d = d[d.ST == "TX"]
    assert d.ST_LEAID.str.fullmatch(r"TX-\d{6}").all(), "unexpected ST_LEAID format"
    out = pd.DataFrame(
        {
            "cdn": d.ST_LEAID.str[3:],
            "leaid": d.LEAID,
            "ccd_name": d.LEA_NAME,
            "lea_type": d.LEA_TYPE_TEXT,
            "charter_lea": d.CHARTER_LEA_TEXT,
            "sy_status": d.SY_STATUS_TEXT,
            "ccd_year": d.SCHOOL_YEAR,
        }
    )
    out.to_parquet(OUT / "ccd_lea.parquet", index=False)
    print(f"ccd lea 2023-24: {len(out):,} Texas LEAs")
    return out


def ingest_edge_lea() -> pd.DataFrame:
    z = fetch(EDGE_LEA_URL, RAW / "nces_edge_lea" / "EDGE_GEOCODE_PUBLICLEA_2425.zip").path
    txt = next(p for p in _unzip(z, z.parent / "x").rglob("*") if p.suffix.upper() == ".TXT")
    d = pd.read_csv(txt, sep="|", header=None, names=EDGE_LEA_FIELDS, dtype=str, encoding="latin-1")
    d = d[d.STFIP == "48"]
    out = pd.DataFrame(
        {
            "leaid": d.LEAID,
            "county_fips": d.CNTY,
            "county_name": d.NMCNTY,
            "cbsa": d.CBSA,
            "cbsa_name": d.NMCBSA,
            "cbsa_type": d.CBSATYPE,
            "locale_code": d.LOCALE,
            "hq_lat": pd.to_numeric(d.LAT),
            "hq_lon": pd.to_numeric(d.LON),
        }
    )
    out.to_parquet(OUT / "edge_lea.parquet", index=False)
    print(f"edge lea geocodes 2024-25: {len(out):,} Texas LEAs")
    return out


def ingest_askted() -> pd.DataFrame:
    dest = RAW / "tea_askted" / "askted_school_district.csv"
    if not dest.exists():
        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT
        page = s.get(ASKTED_URL, timeout=60).text
        form = {
            k: re.search(rf'id="{k}" value="([^"]*)"', page).group(1)
            for k in ["__VIEWSTATE", "__VIEWSTATEGENERATOR"]
        }
        form.update({"ddlSortOrder": "School Number", "btnDownloadFile": "Download File"})
        r = s.post(ASKTED_URL, data=form, timeout=300)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
    d = pd.read_csv(dest, dtype=str)
    d = d.apply(
        lambda c: c.str.lstrip("'") if pd.api.types.is_string_dtype(c) else c
    )  # TEA prefixes codes with '
    d.to_parquet(OUT / "askted.parquet", index=False)
    n_d = d["District Number"].nunique()
    print(f"askted: {len(d):,} campus rows, {n_d:,} districts")
    return d


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ingest_boundaries()
    ingest_ccd_lea()
    ingest_edge_lea()
    ingest_askted()


if __name__ == "__main__":
    main()
