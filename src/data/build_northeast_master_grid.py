"""
build_northeast_master_grid.py

Constructs the Northeast (NE) master daily spatio-temporal grid for flood onset (Task A)
and inundation persistence (Task B) modeling across Assam and Brahmaputra basin stations.

Strictly non-destructive: reads source Northeast tables and exports to
data/processed/northeast/ne_master_daily_grid.parquet without modifying Maharashtra files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Set

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pravah.ne_grid")

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_NE_DIR = REPO_ROOT / "data" / "raw" / "northeast"
PROCESSED_NE_DIR = REPO_ROOT / "data" / "processed" / "northeast"
PROCESSED_MH_DIR = REPO_ROOT / "data" / "processed"

STATIC_NE_PATH = PROCESSED_NE_DIR / "northeast_candidate_static_features.csv"
STATION_CATALOG_PATH = PROCESSED_NE_DIR / "station_catalog.csv"
DAILY_FEATURES_PATH = PROCESSED_NE_DIR / "daily_observation_features.csv"
FLOOD_INVENTORY_PATH = RAW_NE_DIR / "flood_events" / "india_flood_inventory_v3" / "India_Flood_Inventory_v3.csv"
MH_CHARACTERISTICS_PATH = PROCESSED_MH_DIR / "target_catchment_characteristics.csv"

OUTPUT_PARQUET_PATH = PROCESSED_NE_DIR / "ne_master_daily_grid.parquet"
OUTPUT_SUMMARY_PATH = PROCESSED_NE_DIR / "ne_grid_summary.json"


def load_and_filter_flood_events() -> pd.DataFrame:
    """Load India Flood Inventory v3 and isolate validated Assam flood events."""
    if not FLOOD_INVENTORY_PATH.exists():
        logger.warning("Flood inventory not found at %s. Proceeding with threshold-only labeling.", FLOOD_INVENTORY_PATH)
        return pd.DataFrame()

    df = pd.read_csv(FLOOD_INVENTORY_PATH, low_memory=False)
    assam = df[df["State"].astype(str).str.contains("Assam", case=False, na=False)].copy()
    
    assam["start_dt"] = pd.to_datetime(assam["Start Date"], format="%d-%m-%Y %H:%M", errors="coerce")
    fallback_start = pd.to_datetime(assam["Start Date"], errors="coerce")
    assam["start_dt"] = assam["start_dt"].fillna(fallback_start)

    assam["end_dt"] = pd.to_datetime(assam["End Date"], format="%d-%m-%Y %H:%M", errors="coerce")
    fallback_end = pd.to_datetime(assam["End Date"], errors="coerce")
    assam["end_dt"] = assam["end_dt"].fillna(fallback_end)
    assam["end_dt"] = assam["end_dt"].fillna(assam["start_dt"] + pd.Timedelta(days=2))

    assam = assam.dropna(subset=["start_dt"]).copy()
    assam["Districts_clean"] = assam["Districts"].astype(str).str.upper()
    logger.info("Loaded %d validated Assam flood event records", len(assam))
    return assam


def compute_station_antecedent_features(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand daily observation series into regular continuous daily timeline per station
    and compute rolling Antecedent Precipitation Index (API) features without future leakage.
    """
    daily_df["Date"] = pd.to_datetime(daily_df["Date"])
    records = []

    for station, group in daily_df.groupby("Station"):
        grp = group.sort_values("Date").drop_duplicates(subset=["Date"]).set_index("Date")
        state = grp["State"].dropna().iloc[0] if not grp["State"].dropna().empty else "Assam"
        district = grp["District"].dropna().iloc[0] if not grp["District"].dropna().empty else "Unknown"

        # Create continuous date range to ensure rolling sums accurately reflect calendar days
        full_idx = pd.date_range(grp.index.min(), grp.index.max(), freq="D")
        reindexed = grp.reindex(full_idx)
        reindexed["rainfall_mm"] = reindexed["rainfall_mm"].fillna(0.0)
        reindexed["Station"] = station
        reindexed["State"] = state
        reindexed["District"] = district

        rain = reindexed["rainfall_mm"]

        # Shift by 1 day so Day T features reflect solely antecedent values P_{T-10}...P_{T-1}
        rain_prev1 = rain.shift(1).fillna(0.0)
        rain_prev2 = rain.shift(2).fillna(0.0)
        rain_prev3 = rain.shift(3).fillna(0.0)

        p_1d = rain_prev1
        p_2d_sum = rain_prev1 + rain_prev2
        p_3d_sum = rain.rolling(3).sum().shift(1).fillna(0.0)
        p_5d_sum = rain.rolling(5).sum().shift(1).fillna(0.0)
        p_7d_sum = rain.rolling(7).sum().shift(1).fillna(0.0)
        p_10d_sum = rain.rolling(10).sum().shift(1).fillna(0.0)

        p_3d_max = rain.rolling(3).max().shift(1).fillna(0.0)
        p_7d_max = rain.rolling(7).max().shift(1).fillna(0.0)

        # Dry days (< 1.0 mm) in preceding 3 days
        dry_flag = (rain < 1.0).astype(float)
        p_dry_days_3d = dry_flag.rolling(3).sum().shift(1).fillna(3.0)

        reindexed["rain_1d"] = p_1d
        reindexed["rain_2d_sum"] = p_2d_sum
        reindexed["rain_3d_sum"] = p_3d_sum
        reindexed["rain_5d_sum"] = p_5d_sum
        reindexed["rain_7d_sum"] = p_7d_sum
        reindexed["rain_10d_sum"] = p_10d_sum
        reindexed["rain_3d_max"] = p_3d_max
        reindexed["rain_7d_max"] = p_7d_max
        reindexed["rain_dry_days_3d"] = p_dry_days_3d
        reindexed["has_gpm_coverage"] = 1

        reindexed["Date"] = reindexed.index
        records.append(reindexed)

    result = pd.concat(records, ignore_index=True)
    logger.info("Constructed continuous daily grid: %d rows across %d stations", len(result), result["Station"].nunique())
    return result


def label_flood_events(grid: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign Task A (Flood Onset within 24h) and Task B (Active Flood Inundation) labels
    based on district-matched inventory records and water level telemetry thresholds.
    """
    grid["target_onset"] = 0
    grid["target_active"] = 0

    if not events_df.empty:
        for district, d_events in events_df.groupby("Districts_clean"):
            # Find matching station rows where station district appears in the event district string
            station_mask = grid["District"].str.upper().apply(lambda d: d in district or district in d)
            if not station_mask.any():
                continue

            sub_indices = grid[station_mask].index

            for _, ev in d_events.iterrows():
                ev_start = ev["start_dt"].normalize()
                ev_end = ev["end_dt"].normalize()

                # Task A: Flood onset within 24 hours (day of onset or 1 day prior)
                onset_mask = (grid.loc[sub_indices, "Date"] >= ev_start - pd.Timedelta(days=1)) & \
                             (grid.loc[sub_indices, "Date"] <= ev_start)
                grid.loc[sub_indices[onset_mask], "target_onset"] = 1

                # Task B: Active inundation duration
                active_mask = (grid.loc[sub_indices, "Date"] >= ev_start) & \
                              (grid.loc[sub_indices, "Date"] <= ev_end)
                grid.loc[sub_indices[active_mask], "target_active"] = 1

    # Water level threshold additions (95th percentile stage)
    if "water_level_m" in grid.columns:
        valid_wl = grid[grid["water_level_m"].notna()]
        if not valid_wl.empty:
            q95 = valid_wl.groupby("Station")["water_level_m"].transform(lambda s: s.quantile(0.95))
            high_stage = (valid_wl["water_level_m"] >= q95) & (valid_wl["water_level_m"] > 5.0)
            high_indices = valid_wl[high_stage].index
            grid.loc[high_indices, "target_active"] = 1

    onset_count = int(grid["target_onset"].sum())
    active_count = int(grid["target_active"].sum())
    logger.info("Assigned ground-truth targets: Task A Onset=%d (%.2f%%), Task B Active=%d (%.2f%%)",
                onset_count, 100 * onset_count / len(grid), active_count, 100 * active_count / len(grid))
    return grid


def merge_static_characteristics(grid: pd.DataFrame) -> pd.DataFrame:
    """
    Merge HydroBASINS static features and join/impute 107 INDOFLOODS static attributes
    so that model pipelines can operate on a unified, standardized schema.
    """
    # Load candidate static features
    if STATIC_NE_PATH.exists():
        static_ne = pd.read_csv(STATIC_NE_PATH)
        # Deduplicate on StationID
        static_ne = static_ne.drop_duplicates(subset=["StationID"]).copy()
    else:
        static_ne = pd.DataFrame()

    # Load baseline Maharashtra characteristics to obtain the canonical 107 feature template
    if MH_CHARACTERISTICS_PATH.exists():
        mh_chars = pd.read_csv(MH_CHARACTERISTICS_PATH)
        # Compute regional medians for imputation of morphometric/climate parameters
        num_cols = mh_chars.select_dtypes(include=["number"]).columns
        median_defaults = mh_chars[num_cols].median().to_dict()
    else:
        median_defaults = {}

    # Merge HydroBASINS static attributes to grid
    if not static_ne.empty:
        ne_cols_to_merge = [c for c in ["StationID", "basin_area_km2", "upstream_area_km2", "ORDER", "DIST_MAIN", "DIST_SINK"] if c in static_ne.columns]
        grid = grid.merge(static_ne[ne_cols_to_merge], left_on="Station", right_on="StationID", how="left")
        if "StationID" in grid.columns:
            grid = grid.drop(columns=["StationID"])

    # Provide defaults for terrain / catchment slope
    # Brahmaputra basin / Assam foothill tributaries have mean slopes ~ 0.045 to 0.080 m/m
    # Build static defaults dictionary
    new_cols = {
        "Catchment Relief": 850.0,
        "Drainage Area": grid["basin_area_km2"].fillna(250.0) if "basin_area_km2" in grid.columns else 250.0,
        "Downvalley Length": grid["DIST_MAIN"].fillna(35000.0) if "DIST_MAIN" in grid.columns else 35000.0,
        "Stream Order": grid["ORDER"].fillna(3) if "ORDER" in grid.columns else 3,
        "slope": 0.052,
        "rain_1d_x_slope": grid["rain_1d"] * 0.052,
        "rain_3d_x_slope": grid["rain_3d_sum"] * 0.052,
        "GaugeID": grid["Station"].astype(str),
        "River_Name": "Brahmaputra / Tributary",
        "Basin": "Brahmaputra",
        "Privacy": "Open",
        "KoppenGeiger Climate Type": "Humid subtropical",
        "Land cover": "Cropland / Mosaic vegetation",
        "Soil type": "Fluvisols / Alluvial",
        "lithology type": "Siliciclastic sedimentary rocks",
    }

    for col, default_val in median_defaults.items():
        if col not in grid.columns and col not in new_cols:
            new_cols[col] = default_val

    grid = pd.concat([grid, pd.DataFrame(new_cols, index=grid.index)], axis=1)
    return grid.copy()


def assign_spatio_temporal_splits(grid: pd.DataFrame) -> pd.DataFrame:
    """
    Assign leak-free temporal holdout splits:
    - Train: 2001-01-01 to 2020-12-31
    - Val:   2021-01-01 to 2022-12-31
    - Test:  2023-01-01 to 2026-12-31
    """
    split = pd.Series("train", index=grid.index)
    split.loc[(grid["Date"] >= "2021-01-01") & (grid["Date"] < "2023-01-01")] = "val"
    split.loc[grid["Date"] >= "2023-01-01"] = "test"
    grid["split"] = split

    split_counts = grid["split"].value_counts().to_dict()
    logger.info("Assigned temporal splits: %s", split_counts)
    return grid


def main():
    logger.info("Starting Northeast Master Daily Grid Construction...")
    PROCESSED_NE_DIR.mkdir(parents=True, exist_ok=True)

    daily_obs = pd.read_csv(DAILY_FEATURES_PATH)
    events_df = load_and_filter_flood_events()

    # Step 1: Continuous daily sequence & Antecedent Precipitation Index (API)
    grid = compute_station_antecedent_features(daily_obs)

    # Step 2: Flood onset & persistence labels
    grid = label_flood_events(grid, events_df)

    # Step 3: Join static morphometrics & interaction features
    grid = merge_static_characteristics(grid)

    # Step 4: Spatio-temporal leak-free splitting
    grid = assign_spatio_temporal_splits(grid)

    # Save to parquet and csv.gz
    grid.to_parquet(OUTPUT_PARQUET_PATH, index=False)
    csv_gz_path = PROCESSED_NE_DIR / "ne_master_daily_grid.csv.gz"
    grid.to_csv(csv_gz_path, index=False, compression="gzip")
    logger.info("Successfully exported master daily grid to %s and %s (%d rows, %d cols)",
                OUTPUT_PARQUET_PATH, csv_gz_path, len(grid), len(grid.columns))

    # Save summary metadata
    summary = {
        "total_rows": len(grid),
        "total_stations": int(grid["Station"].nunique()),
        "columns_count": len(grid.columns),
        "date_range": [grid["Date"].min().isoformat(), grid["Date"].max().isoformat()],
        "splits": grid["split"].value_counts().to_dict(),
        "task_a_onset_positives": int(grid["target_onset"].sum()),
        "task_b_active_positives": int(grid["target_active"].sum()),
        "task_a_onset_rate_percent": round(100 * float(grid["target_onset"].mean()), 4),
        "task_b_active_rate_percent": round(100 * float(grid["target_active"].mean()), 4),
    }
    with OUTPUT_SUMMARY_PATH.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    logger.info("Saved summary metadata to %s", OUTPUT_SUMMARY_PATH)
    print("\n=== Northeast Master Grid Summary ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
