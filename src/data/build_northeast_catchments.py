"""Build station-linked candidate catchments from HydroBASINS polygons.

HydroBASINS provides nested basin polygons, not surveyed gauge-specific
upstream delineations. The output is therefore a candidate spatial layer and
must be reviewed before use as a final catchment label.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
STATION_PATH = REPO_ROOT / "data" / "processed" / "northeast" / "station_catalog.csv"
BASIN_PATH = (
    REPO_ROOT
    / "data"
    / "raw"
    / "northeast"
    / "catchments"
    / "hydrobasins_as_level12"
    / "hybas_as_lev12_v1c.shp"
)
OUTPUT_ROOT = REPO_ROOT / "data" / "processed" / "northeast"


def main() -> None:
    stations = pd.read_csv(STATION_PATH)
    basins = gpd.read_file(BASIN_PATH)
    points = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations["Longitude"], stations["Latitude"]),
        crs="EPSG:4326",
    )
    if basins.crs is None:
        raise ValueError("HydroBASINS source has no CRS")
    points = points.to_crs(basins.crs)
    matched = gpd.sjoin(basins, points, how="inner", predicate="contains")
    if matched.empty:
        matched = gpd.sjoin(basins, points, how="inner", predicate="intersects")
    if matched.empty:
        raise ValueError("No Northeast stations intersected HydroBASINS polygons")

    matched = matched.rename(columns={"StationID": "station_id", "Station": "station_name"})
    matched["source"] = "HydroBASINS v1c Asia level 12"
    matched["catchment_status"] = "candidate_point_matched"
    output_columns = [
        "station_id",
        "station_name",
        "State",
        "District",
        "Latitude",
        "Longitude",
        "HYBAS_ID",
        "SUB_AREA",
        "UP_AREA",
        "PFAF_ID",
        "source",
        "catchment_status",
        "geometry",
    ]
    output_columns = [column for column in output_columns if column in matched.columns]
    matched[output_columns].to_file(
        OUTPUT_ROOT / "northeast_candidate_catchments.geojson", driver="GeoJSON"
    )

    static = matched.drop(columns="geometry").copy()
    static = static.rename(
        columns={
            "station_id": "StationID",
            "SUB_AREA": "basin_area_km2",
            "UP_AREA": "upstream_area_km2",
            "PFAF_ID": "pfaf_id",
        }
    )
    static.to_csv(OUTPUT_ROOT / "northeast_candidate_static_features.csv", index=False)
    print(f"[INFO] Wrote {len(matched)} station-basin matches")
    print(f"[INFO] Wrote {matched['station_id'].nunique()} unique station matches")
    print("[INFO] Catchments remain candidates until gauge-specific upstream boundaries are verified")


if __name__ == "__main__":
    main()