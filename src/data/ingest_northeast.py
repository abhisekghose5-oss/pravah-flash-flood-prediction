"""Normalize supplied Northeast rainfall and water-level source files."""

from pathlib import Path
import json

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "data" / "raw" / "northeast"
PROCESSED_ROOT = REPO_ROOT / "data" / "processed" / "northeast"
TIME_FORMAT = "%d-%m-%Y %H:%M"


def _read_csvs(directory: Path, pattern: str) -> list[tuple[str, pd.DataFrame]]:
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern} in {directory}")
    return [(file.name, pd.read_csv(file, low_memory=False)) for file in files]


def load_rainfall_observations() -> pd.DataFrame:
    frames = []
    for source_file, frame in _read_csvs(RAW_ROOT / "rainfall", "rainfall_manual_*.csv"):
        required = {"Station", "State", "District", "Latitude", "Longitude", "Data Acquisition Time", "Manual Daily Rainfall (mm)"}
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{source_file} is missing rainfall columns: {sorted(missing)}")
        normalized = frame[
            ["Station", "State", "District", "Latitude", "Longitude", "Data Acquisition Time", "Manual Daily Rainfall (mm)"]
        ].copy()
        normalized["timestamp"] = pd.to_datetime(
            normalized.pop("Data Acquisition Time"), format=TIME_FORMAT, errors="coerce"
        )
        normalized = normalized.rename(columns={"Manual Daily Rainfall (mm)": "rainfall_mm"})
        normalized["rainfall_mm"] = pd.to_numeric(normalized["rainfall_mm"], errors="coerce")
        normalized = normalized.dropna(subset=["rainfall_mm"])
        normalized["source_file"] = source_file
        frames.append(normalized)

    result = pd.concat(frames, ignore_index=True)
    if result["timestamp"].isna().any():
        raise ValueError("Rainfall data contains unparseable acquisition timestamps")
    return result.sort_values(["Station", "timestamp"]).reset_index(drop=True)


def load_water_level_observations() -> pd.DataFrame:
    frames = []
    for source_file, frame in _read_csvs(RAW_ROOT / "water_level", "rwl_*.csv"):
        required = {"Station", "State", "District", "Latitude", "Longitude", "Data Acquisition Time", "River Water Level Telemetry Hourly (meter)"}
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{source_file} is missing water-level columns: {sorted(missing)}")
        normalized = frame[
            ["Station", "State", "District", "Latitude", "Longitude", "Data Acquisition Time", "River Water Level Telemetry Hourly (meter)"]
        ].copy()
        normalized["timestamp"] = pd.to_datetime(
            normalized.pop("Data Acquisition Time"), format=TIME_FORMAT, errors="coerce"
        )
        normalized = normalized.rename(columns={"River Water Level Telemetry Hourly (meter)": "water_level_m"})
        normalized["water_level_m"] = pd.to_numeric(normalized["water_level_m"], errors="coerce")
        normalized = normalized.dropna(subset=["water_level_m"])
        normalized["source_file"] = source_file
        frames.append(normalized)

    result = pd.concat(frames, ignore_index=True)
    if result["timestamp"].isna().any():
        raise ValueError("Water-level data contains unparseable acquisition timestamps")
    return result.sort_values(["Station", "timestamp"]).reset_index(drop=True)


def build_station_catalog(rainfall: pd.DataFrame, water_level: pd.DataFrame) -> pd.DataFrame:
    observations = pd.concat(
        [
            rainfall.assign(observation_type="rainfall"),
            water_level.assign(observation_type="water_level"),
        ],
        ignore_index=True,
    )
    catalog = (
        observations.groupby(["Station", "State", "District"], dropna=False)
        .agg(
            Latitude=("Latitude", "first"),
            Longitude=("Longitude", "first"),
            first_observation=("timestamp", "min"),
            last_observation=("timestamp", "max"),
            observation_count=("timestamp", "size"),
            observation_types=("observation_type", lambda values: ",".join(sorted(set(values)))),
        )
        .reset_index()
    )
    catalog.insert(0, "StationID", catalog["Station"].astype(str).str.strip())
    return catalog.sort_values("StationID").reset_index(drop=True)


def build_daily_features(rainfall: pd.DataFrame, water_level: pd.DataFrame) -> pd.DataFrame:
    rainfall_daily = (
        rainfall.assign(Date=rainfall["timestamp"].dt.normalize())
        .groupby(["Station", "State", "District", "Date"], as_index=False)
        .agg(rainfall_mm=("rainfall_mm", "sum"))
    )
    rainfall_daily["rain_1d"] = rainfall_daily["rainfall_mm"]
    rainfall_daily["rain_3d_sum"] = rainfall_daily.groupby("Station")["rainfall_mm"].transform(
        lambda values: values.rolling(3, min_periods=1).sum()
    )
    rainfall_daily["rain_7d_sum"] = rainfall_daily.groupby("Station")["rainfall_mm"].transform(
        lambda values: values.rolling(7, min_periods=1).sum()
    )

    water_level_daily = (
        water_level.assign(Date=water_level["timestamp"].dt.normalize())
        .groupby(["Station", "State", "District", "Date"], as_index=False)
        .agg(
            water_level_m=("water_level_m", "mean"),
            water_level_max_m=("water_level_m", "max"),
            water_level_observations=("water_level_m", "count"),
        )
    )
    features = rainfall_daily.merge(
        water_level_daily,
        on=["Station", "State", "District", "Date"],
        how="outer",
    )
    return features.sort_values(["Station", "Date"]).reset_index(drop=True)


def build_quality_summary(rainfall: pd.DataFrame, water_level: pd.DataFrame) -> dict:
    return {
        "region": "Northeast India",
        "rainfall_observations": int(len(rainfall)),
        "water_level_observations": int(len(water_level)),
        "rainfall_stations": int(rainfall["Station"].nunique()),
        "water_level_stations": int(water_level["Station"].nunique()),
        "rainfall_missing_values": int(rainfall["rainfall_mm"].isna().sum()),
        "water_level_missing_values": int(water_level["water_level_m"].isna().sum()),
        "water_level_duplicate_station_timestamps": int(
            water_level.duplicated(["Station", "timestamp"]).sum()
        ),
        "rainfall_date_range": [
            rainfall["timestamp"].min().date().isoformat(),
            rainfall["timestamp"].max().date().isoformat(),
        ],
        "water_level_date_range": [
            water_level["timestamp"].min().date().isoformat(),
            water_level["timestamp"].max().date().isoformat(),
        ],
        "training_blockers": [
            "verified_flood_event_labels",
            "gauge_linked_catchment_polygons",
            "static_catchment_features",
            "warning_and_danger_levels",
        ],
    }


def main() -> None:
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    rainfall = load_rainfall_observations()
    water_level = load_water_level_observations()
    station_catalog = build_station_catalog(rainfall, water_level)
    daily_features = build_daily_features(rainfall, water_level)
    rainfall.to_csv(PROCESSED_ROOT / "rainfall_observations.csv", index=False)
    water_level.to_csv(PROCESSED_ROOT / "water_level_observations.csv", index=False)
    station_catalog.to_csv(PROCESSED_ROOT / "station_catalog.csv", index=False)
    daily_features.to_csv(PROCESSED_ROOT / "daily_observation_features.csv", index=False)
    (PROCESSED_ROOT / "quality_summary.json").write_text(
        json.dumps(build_quality_summary(rainfall, water_level), indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] Wrote {len(rainfall)} Northeast rainfall observations")
    print(f"[INFO] Wrote {len(water_level)} Northeast water-level observations")
    print(f"[INFO] Wrote {len(station_catalog)} Northeast station records")
    print(f"[INFO] Wrote {len(daily_features)} Northeast daily feature rows")
    print("[INFO] Flood labels and catchment joins are still required before ML training")


if __name__ == "__main__":
    main()