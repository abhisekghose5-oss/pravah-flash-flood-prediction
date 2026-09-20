from pathlib import Path

from src.data.ingest_northeast import (
    build_daily_features,
    build_station_catalog,
    load_rainfall_observations,
    load_water_level_observations,
)


def test_northeast_source_files_are_present():
    root = Path(__file__).resolve().parents[1] / "data" / "raw" / "northeast"
    assert list((root / "rainfall").glob("*.csv"))
    assert list((root / "water_level").glob("*.csv"))


def test_northeast_observations_normalize_with_coordinates_and_time():
    rainfall = load_rainfall_observations()
    water_level = load_water_level_observations()

    for frame, value_column in ((rainfall, "rainfall_mm"), (water_level, "water_level_m")):
        assert frame["timestamp"].notna().all()
        assert frame["Latitude"].between(-90, 90).all()
        assert frame["Longitude"].between(-180, 180).all()
        assert frame[value_column].notna().all()
        assert frame["source_file"].notna().all()


def test_northeast_derived_artifacts_have_expected_keys():
    rainfall = load_rainfall_observations()
    water_level = load_water_level_observations()
    catalog = build_station_catalog(rainfall, water_level)
    daily = build_daily_features(rainfall, water_level)

    assert catalog["StationID"].notna().all()
    assert catalog["StationID"].is_unique
    assert daily[["Station", "Date"]].drop_duplicates().shape[0] == len(daily)
    assert {"rain_1d", "rain_3d_sum", "rain_7d_sum"}.issubset(daily.columns)