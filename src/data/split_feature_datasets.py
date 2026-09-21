"""Create named feature views without changing PRAVAH model input files."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
OUTPUT_DIR = PROCESSED_DIR / "feature_views"


def clean_gauge_id(value: object) -> str:
    text = str(value).strip()
    digits = "".join(character for character in text if character.isdigit())
    return digits or text


def with_key(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["GaugeID"] = result["GaugeID"].map(clean_gauge_id)
    return result


def select_existing(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    selected = [column for column in columns if column in frame.columns]
    return frame[selected].copy()


def build_views() -> None:
    spatial = with_key(pd.read_csv(PROCESSED_DIR / "target_catchment_spatial_features.csv"))
    characteristics = with_key(pd.read_csv(PROCESSED_DIR / "target_catchment_characteristics.csv"))

    if spatial["GaugeID"].duplicated().any() or characteristics["GaugeID"].duplicated().any():
        raise ValueError("Source feature tables contain duplicate GaugeID values.")

    joined = characteristics.merge(spatial, on="GaugeID", how="left", validate="one_to_one")
    if len(joined) != len(characteristics) or joined["GaugeID"].isna().any():
        raise ValueError("Feature views would change the source GaugeID linkage.")

    views = {
        "terrain_and_morphometry.csv": select_existing(
            joined,
            [
                "GaugeID", "dem_elev_mean_m", "dem_elev_min_m", "dem_elev_max_m",
                "dem_elev_std_m", "terrain_slope_mean_deg", "terrain_aspect_deg_mean",
                "twi_mean", "tri_mean", "Catchment Relief", "Drainage Area",
                "Drainage Density", "Stream Order", "Ruggedness Number",
            ],
        ),
        "soil_landcover_geology.csv": select_existing(
            joined, ["GaugeID", "Soil type", "Land cover", "lithology type"]
        ),
        "atmospheric_climate.csv": select_existing(
            joined,
            [
                "GaugeID", "Annual Mean Temperature", "Mean Diurnal Range",
                "Isothermality", "Temperature Seasonality", "Max Temperature of Warmest Month",
                "Min Temperature of Coldest Month", "Temperature Annual Range",
                "Mean Temperature of Wettest Quarter", "Mean Temperature of Driest Quarter",
                "Mean Temperature of Warmest Quarter", "Mean Temperature of Coldest Quarter",
                "Annual Precipitation", "Precipitation of Wettest Month",
                "Precipitation of Driest Month", "Precipitation Seasonality",
                "Precipitation of Wettest Quarter", "Precipitation of Driest Quarter",
                "Precipitation of Warmest Quarter", "Precipitation of Coldest Quarter",
                "KoppenGeiger Climate Type",
            ],
        ),
        "population_landuse_infrastructure.csv": select_existing(
            joined,
            [
                "GaugeID", "Population Count", "Population Density", "Night Light",
                "Road Density", "Urban percentage", "2010_HDI", "2015_HDI",
                "Land cover", "road_density_km_per_km2", "hospital_count",
                "nearest_hospital_distance_km", "population_total",
                "population_density_per_km2", "urban_built_up_pct", "dense_forest_pct",
                "agriculture_pct", "water_body_pct", "barren_rocky_pct",
                "impervious_surface_pct",
            ],
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "join_key": "GaugeID",
        "source_files": [
            "target_catchment_characteristics.csv",
            "target_catchment_spatial_features.csv",
        ],
        "canonical_inputs_unchanged": True,
        "views": {},
    }
    for filename, view in views.items():
        view.to_csv(OUTPUT_DIR / filename, index=False)
        manifest["views"][filename] = {
            "rows": len(view),
            "columns": list(view.columns),
        }

    (OUTPUT_DIR / "README.md").write_text(
        "# Named feature views\n\n"
        "These CSVs are derived from the canonical processed catchment tables. "
        "Every view keeps the original cleaned `GaugeID` so it can be joined without changing backend or ML contracts. "
        "The inference engine and training artifacts continue to use their existing canonical files.\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "feature_views_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build_views()
    print(f"Created {len(list(OUTPUT_DIR.glob('*.csv')))} named feature views in {OUTPUT_DIR}")