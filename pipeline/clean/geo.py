"""Build the committed, simplified map layers in data/geo/.

* tx_districts_simplified.geojson: district polygons (unified + elementary; the one secondary-only
  polygon, Hallettsville ISD grades 9-12 inside Vysehrad ISD, is left out of the fill layer because
  it overlaps the elementary district). Simplified with `topojson` (shared arcs, so neighbouring
  districts keep identical borders: no slivers or gaps). Only the GEOID is stored; attributes are
  joined from the marts at runtime.
* tx_counties.geojson, tx_esc_regions.geojson, tx_metros.geojson, tx_outline.geojson: light
  overlays. ESC regions are dissolved from district polygons using AskTED's
  "ESC Region Geographic" field. Counties, metros (CBSA type 1 = metropolitan) and the state
  outline are Census cartographic boundary files (2024, 1:500k).

Checks (run on every build): all simplified district polygons valid before writing; total area
within 1% of the unsimplified polygons (actual: -0.001%). After rounding coordinates to 5 decimals
(~1 m), a handful of polygons have sub-metre self-touches; these files are for display only, and
all spatial computation in the pipeline uses the unsimplified boundaries.
"""

from __future__ import annotations

import json
import zipfile

import geopandas as gpd
import pandas as pd
import topojson as tp
from shapely import make_valid
from shapely.ops import unary_union

from pipeline.ingest._http import RAW, ROOT, fetch

GEO = ROOT / "data" / "geo"
PROC = ROOT / "data" / "processed"
CB = "https://www2.census.gov/geo/tiger/GENZ2024/shp/{name}.zip"
TOLERANCE = 0.004  # degrees (about 400 m); checked visually and against the 6 MB budget
PRECISION = 5  # decimal places in output coordinates (about 1 m)


def _cb(name: str) -> gpd.GeoDataFrame:
    z = fetch(CB.format(name=name), RAW / "census_cb" / f"{name}.zip").path
    with zipfile.ZipFile(z) as zf:
        zf.extractall(z.parent / name)
    return gpd.read_file(next((z.parent / name).glob("*.shp")))


def _write(gdf: gpd.GeoDataFrame, name: str) -> None:
    path = GEO / name
    gdf = gdf.to_crs(4326)
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    data = json.loads(gdf.to_json(drop_id=True))

    def rnd(c):
        return [rnd(x) for x in c] if isinstance(c[0], list) else [round(v, PRECISION) for v in c]

    for f in data["features"]:
        f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
    path.write_text(json.dumps(data, separators=(",", ":")))
    print(f"{name}: {len(gdf)} features, {path.stat().st_size / 1e6:.2f} MB")


def _polygonal(geom):
    """make_valid can return a GeometryCollection; keep only its polygon parts."""
    geom = make_valid(geom)
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(parts)


def _simplify(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.assign(geometry=gdf.geometry.apply(_polygonal))
    topo = tp.Topology(gdf, prequantize=False, toposimplify=TOLERANCE, prevent_oversimplify=True)
    out = topo.to_gdf()
    # Douglas-Peucker on shared arcs can leave small self-intersections (mostly along the coast);
    # make_valid splits them without moving the shared borders.
    return out.assign(geometry=out.geometry.apply(_polygonal)).set_crs(4326, allow_override=True)


def build() -> None:
    GEO.mkdir(parents=True, exist_ok=True)
    b = gpd.read_parquet(PROC / "boundaries.parquet")
    b = b[b.sd_type != "secondary"][["geoid", "geometry"]].to_crs(4326)
    districts = _simplify(b)
    assert districts.is_valid.all(), "simplification produced invalid geometries"
    # quality checks against the unsimplified polygons (equal-area projection, EPSG:3083)
    a0 = b.to_crs(3083).area.sum()
    a1 = districts.to_crs(3083).area.sum()
    assert abs(a1 / a0 - 1) < 0.01, f"total area changed by {a1 / a0 - 1:.2%}"
    print(f"area change after simplification: {a1 / a0 - 1:+.3%}")
    _write(districts, "tx_districts_simplified.geojson")

    ask = pd.read_parquet(PROC / "askted.parquet")
    esc = (
        ask[["NCES District ID", "ESC Region Geographic"]]
        .drop_duplicates()
        .rename(columns={"NCES District ID": "geoid", "ESC Region Geographic": "esc_region"})
    )
    regions = (
        b.merge(esc, on="geoid", how="inner")
        .dissolve("esc_region")
        .reset_index()[["esc_region", "geometry"]]
    )
    _write(_simplify(regions), "tx_esc_regions.geojson")

    counties = _cb("cb_2024_us_county_500k")
    counties = counties[counties.STATEFP == "48"][["GEOID", "NAME", "geometry"]].rename(
        columns=str.lower
    )
    _write(_simplify(counties), "tx_counties.geojson")

    state = _cb("cb_2024_us_state_500k")
    _write(
        state[state.STATEFP == "48"][["NAME", "geometry"]]
        .rename(columns=str.lower)
        .assign(geometry=lambda d: d.simplify(TOLERANCE)),
        "tx_outline.geojson",
    )

    cbsa = _cb("cb_2024_us_cbsa_500k")
    tx = state[state.STATEFP == "48"].to_crs(cbsa.crs)
    metros = cbsa[(cbsa.LSAD == "M1") & cbsa.intersects(tx.union_all())][
        ["GEOID", "NAME", "geometry"]
    ]
    metros = metros.clip(tx).rename(columns=str.lower)
    metros = metros.to_crs(4326).assign(geometry=lambda d: d.simplify(TOLERANCE).apply(_polygonal))
    _write(metros, "tx_metros.geojson")


if __name__ == "__main__":
    build()
