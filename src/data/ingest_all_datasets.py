from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pravah.ingest_all_datasets")

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"


def make_geojson_feature(
    geometry_type: str,
    coordinates: List[float],
    properties: Dict[str, Any],
) -> Dict[str, Any]:
    """Helper to format a standard GeoJSON Feature dictionary."""
    return {
        "type": "Feature",
        "geometry": {
            "type": geometry_type,
            "coordinates": coordinates,
        },
        "properties": properties,
    }


def ingest_soil_dataset() -> pd.DataFrame:
    """Ingest and validate soil hydrology profiles."""
    src = RAW_DIR / "soil" / "soil_hydrology_profiles.csv"
    dst = PROCESSED_DIR / "soil_hydrology_features.csv"
    if not src.exists():
        raise FileNotFoundError(f"Missing raw soil dataset: {src}")

    df = pd.read_csv(src)
    required_cols = [
        "GaugeID",
        "soil_order",
        "soil_texture_class",
        "saturated_hydraulic_conductivity_ksat_mm_hr",
        "available_water_capacity_awc_mm_m",
        "hydrologic_soil_group",
        "scs_curve_number_cn2",
    ]
    for col in required_cols:
        assert col in df.columns, f"Soil dataset missing column {col}"

    # Verify physical sanity
    assert (df["scs_curve_number_cn2"] >= 30).all() and (df["scs_curve_number_cn2"] <= 100).all()
    assert (df["saturated_hydraulic_conductivity_ksat_mm_hr"] > 0).all()

    df.to_csv(dst, index=False)
    logger.info("Processed Soil Hydrology features -> %s (%d rows)", dst.name, len(df))
    return df


def ingest_river_levels_dataset() -> pd.DataFrame:
    """Ingest and validate CWC daily river water level telemetry."""
    src = RAW_DIR / "river_levels" / "cwc_daily_river_stages.csv"
    dst = PROCESSED_DIR / "river_level_telemetry.csv"
    if not src.exists():
        raise FileNotFoundError(f"Missing raw river level dataset: {src}")

    df = pd.read_csv(src)
    required_cols = [
        "GaugeID",
        "Station",
        "date",
        "water_level_m",
        "warning_level_m",
        "danger_level_m",
        "freeboard_remaining_m",
        "stage_status",
        "discharge_cumecs",
    ]
    for col in required_cols:
        assert col in df.columns, f"River level dataset missing column {col}"

    df.to_csv(dst, index=False)
    logger.info("Processed River Level telemetry -> %s (%d rows)", dst.name, len(df))
    return df


def ingest_dams_dataset() -> pd.DataFrame:
    """Ingest dams master and generate both CSV and GeoJSON FeatureCollection."""
    src = RAW_DIR / "dams" / "dams_reservoirs_master.csv"
    dst_csv = PROCESSED_DIR / "dams_reservoirs.csv"
    dst_geojson = PROCESSED_DIR / "dams_reservoirs.geojson"
    if not src.exists():
        raise FileNotFoundError(f"Missing raw dams dataset: {src}")

    df = pd.read_csv(src)
    df.to_csv(dst_csv, index=False)

    features = []
    for _, row in df.iterrows():
        props = row.to_dict()
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        features.append(make_geojson_feature("Point", [lon, lat], props))

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    with open(dst_geojson, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    logger.info("Processed Dams dataset -> %s & %s (%d dams)", dst_csv.name, dst_geojson.name, len(df))
    return df


def ingest_terrain_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ingest terrain morphometrics and mountain peaks/passes GeoJSON."""
    src_terr = RAW_DIR / "terrain" / "catchment_terrain_orography.csv"
    dst_terr = PROCESSED_DIR / "mountain_terrain_features.csv"
    df_terr = pd.read_csv(src_terr)
    df_terr.to_csv(dst_terr, index=False)

    src_peaks = RAW_DIR / "terrain" / "mountain_peaks_passes.csv"
    dst_peaks_geojson = PROCESSED_DIR / "mountain_peaks_passes.geojson"
    df_peaks = pd.read_csv(src_peaks)

    features = []
    for _, row in df_peaks.iterrows():
        props = row.to_dict()
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        features.append(make_geojson_feature("Point", [lon, lat], props))

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    with open(dst_peaks_geojson, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    logger.info("Processed Terrain features -> %s & %s", dst_terr.name, dst_peaks_geojson.name)
    return df_terr, df_peaks


def ingest_safe_zones_dataset() -> pd.DataFrame:
    """Ingest safe evacuation zones and generate both CSV and GeoJSON."""
    src = RAW_DIR / "safe_zones" / "safe_zones_registry.csv"
    dst_csv = PROCESSED_DIR / "safe_zones.csv"
    dst_geojson = PROCESSED_DIR / "safe_zones.geojson"
    df = pd.read_csv(src)
    df.to_csv(dst_csv, index=False)

    features = []
    for _, row in df.iterrows():
        props = row.to_dict()
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        features.append(make_geojson_feature("Point", [lon, lat], props))

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    with open(dst_geojson, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    logger.info("Processed Safe Zones -> %s & %s (%d shelters)", dst_csv.name, dst_geojson.name, len(df))
    return df


def ingest_confluences_dataset() -> pd.DataFrame:
    """Ingest river confluences and generate GeoJSON."""
    src = RAW_DIR / "drainage" / "river_confluences_master.csv"
    dst_geojson = PROCESSED_DIR / "drainage_confluences.geojson"
    df = pd.read_csv(src)

    features = []
    for _, row in df.iterrows():
        props = row.to_dict()
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        features.append(make_geojson_feature("Point", [lon, lat], props))

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    with open(dst_geojson, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    logger.info("Processed Confluences -> %s (%d points)", dst_geojson.name, len(df))
    return df


def ingest_disaster_response_dataset() -> pd.DataFrame:
    """Ingest emergency response units."""
    src = RAW_DIR / "disaster_response" / "emergency_response_units.csv"
    dst = PROCESSED_DIR / "disaster_response_units.csv"
    df = pd.read_csv(src)
    df.to_csv(dst, index=False)
    logger.info("Processed Disaster Response units -> %s (%d units)", dst.name, len(df))
    return df


def main() -> None:
    logger.info("🌊 Starting Unified Dataset Ingestion Pipeline...")
    ingest_soil_dataset()
    ingest_river_levels_dataset()
    ingest_dams_dataset()
    ingest_terrain_dataset()
    ingest_safe_zones_dataset()
    ingest_confluences_dataset()
    ingest_disaster_response_dataset()
    logger.info("🎉 All datasets successfully ingested and standardized in data/processed/!")


if __name__ == "__main__":
    main()
