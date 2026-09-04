from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("pravah.inference")

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "models"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CHARACTERISTICS_PATH = PROCESSED_DIR / "target_catchment_characteristics.csv"
METADATA_PATH = PROCESSED_DIR / "target_metadata.csv"
CATCHMENTS_GEOJSON = PROCESSED_DIR / "target_catchments.geojson"
MASTER_GRID_PATH = PROCESSED_DIR / "master_daily_grid_splits.parquet"
METRICS_PATH = PROCESSED_DIR / "model_evaluation_metrics.json"

ANTECEDENT_FEATURE_NAMES = [
    "rain_1d",
    "rain_2d_sum",
    "rain_3d_sum",
    "rain_5d_sum",
    "rain_7d_sum",
    "rain_10d_sum",
    "rain_3d_max",
    "rain_7d_max",
    "rain_dry_days_3d",
    "has_gpm_coverage",
]


def clean_gauge_id(value: Union[str, int]) -> str:
    """Standardize gauge ID format to raw numeric string (e.g. '684')."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    match = re.search(r"(\d+)", text)
    return match.group(1) if match else text


def full_gauge_id(value: Union[str, int]) -> str:
    """Format numeric string to INDOFLOODS-gauge-XXX format."""
    num = clean_gauge_id(value)
    return f"INDOFLOODS-gauge-{num}"


def compute_antecedent_features(rainfall_10d: List[float], has_gpm_coverage: int = 1) -> Dict[str, float]:
    """
    Compute the 9 antecedent rainfall features from a 10-day rainfall sequence.
    rainfall_10d: List of 10 float values in chronological order [P_{T-10}, P_{T-9}, ..., P_{T-1}].
    """
    if len(rainfall_10d) != 10:
        raise ValueError(f"Expected exactly 10 daily rainfall values, got {len(rainfall_10d)}")

    arr = np.array(rainfall_10d, dtype=float)
    if (arr < 0).any():
        raise ValueError("Rainfall values cannot be negative")

    p_1d = arr[-1]                    # Day T-1
    p_2d_sum = np.sum(arr[-2:])       # Days T-2, T-1
    p_3d_sum = np.sum(arr[-3:])       # Days T-3..T-1
    p_5d_sum = np.sum(arr[-5:])       # Days T-5..T-1
    p_7d_sum = np.sum(arr[-7:])       # Days T-7..T-1
    p_10d_sum = np.sum(arr)           # Days T-10..T-1
    p_3d_max = np.max(arr[-3:])
    p_7d_max = np.max(arr[-7:])
    p_dry_days_3d = float(np.sum(arr[-3:] < 1.0))

    return {
        "rain_1d": float(p_1d),
        "rain_2d_sum": float(p_2d_sum),
        "rain_3d_sum": float(p_3d_sum),
        "rain_5d_sum": float(p_5d_sum),
        "rain_7d_sum": float(p_7d_sum),
        "rain_10d_sum": float(p_10d_sum),
        "rain_3d_max": float(p_3d_max),
        "rain_7d_max": float(p_7d_max),
        "rain_dry_days_3d": float(p_dry_days_3d),
        "has_gpm_coverage": int(has_gpm_coverage),
    }


def determine_alert_tier(onset_prob: float, onset_threshold: float, active_prob: float, active_threshold: float) -> Tuple[str, str, str]:
    """
    Assign early warning alert tier based on calibrated probabilities and tuned decision thresholds.
    Returns: (tier_name, color_code, recommendation)
    """
    # Emergency: High onset probability or active flood confirmed
    if onset_prob >= 1.5 * onset_threshold or (active_prob >= active_threshold and onset_prob >= onset_threshold):
        return (
            "EMERGENCY",
            "RED",
            "Severe flood event imminent or active. Initiate emergency response and evacuation protocols."
        )
    # Warning: Onset probability exceeds tuned decision threshold
    elif onset_prob >= onset_threshold or active_prob >= active_threshold:
        return (
            "WARNING",
            "ORANGE",
            "High probability of flood onset. Issue early warning to vulnerable riverine communities."
        )
    # Advisory: Elevated antecedent rainfall, approaching threshold
    elif onset_prob >= 0.5 * onset_threshold or active_prob >= 0.5 * active_threshold:
        return (
            "ADVISORY",
            "YELLOW",
            "Moderate catchment saturation. Monitor rainfall intensity and river water levels closely."
        )
    # Normal: Low risk
    else:
        return (
            "NORMAL",
            "GREEN",
            "Low flood risk under current antecedent catchment conditions."
        )


class PravahInferenceEngine:
    """
    Production-grade inference engine for the PRAVAH flash-flood prediction system.
    """

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or MODELS_DIR
        self._models: Dict[str, Dict[str, Any]] = {}
        self._static_characteristics: Optional[pd.DataFrame] = None
        self._station_metadata: Optional[pd.DataFrame] = None
        self._master_grid: Optional[pd.DataFrame] = None
        self._metrics_summary: Optional[Dict[str, Any]] = None

        self._load_metadata()
        self._load_models()

    def _load_metadata(self) -> None:
        """Load and index static catchment characteristics and station metadata."""
        if CHARACTERISTICS_PATH.exists():
            chars = pd.read_csv(CHARACTERISTICS_PATH)
            chars = chars.assign(clean_gauge_id=chars["GaugeID"].map(clean_gauge_id))
            self._static_characteristics = chars.set_index("clean_gauge_id")
            logger.info("Loaded static characteristics for %d catchments", len(self._static_characteristics))

        if METADATA_PATH.exists():
            meta = pd.read_csv(METADATA_PATH)
            meta = meta.assign(clean_gauge_id=meta["GaugeID"].map(clean_gauge_id))
            self._station_metadata = meta.set_index("clean_gauge_id")
            logger.info("Loaded station metadata for %d gauges", len(self._station_metadata))

        if METRICS_PATH.exists():
            with METRICS_PATH.open("r", encoding="utf-8") as fh:
                self._metrics_summary = json.load(fh)

    def _load_models(self) -> None:
        """Load serialized .joblib models and their threshold metadata."""
        for joblib_file in self.models_dir.glob("*.joblib"):
            try:
                bundle = joblib.load(joblib_file)
                self._models[joblib_file.stem] = bundle
                logger.info("Loaded model bundle: %s", joblib_file.stem)
            except Exception as e:
                logger.warning("Failed to load model %s: %s", joblib_file.name, e)

    @property
    def available_models(self) -> List[str]:
        return list(self._models.keys())

    @property
    def registered_gauges(self) -> List[str]:
        if self._static_characteristics is not None:
            return sorted(self._static_characteristics.index.tolist())
        return []

    def get_station_info(self, gauge_id: Union[str, int]) -> Dict[str, Any]:
        """Retrieve static station metadata for a given gauge."""
        gid = clean_gauge_id(gauge_id)
        if self._station_metadata is not None and gid in self._station_metadata.index:
            row = self._station_metadata.loc[gid]
            return {
                "gauge_id": gid,
                "full_gauge_id": full_gauge_id(gid),
                "station_name": str(row.get("Station", "Unknown")),
                "river": str(row.get("River_Name", "Unknown")),
                "basin": str(row.get("Basin", "Unknown")),
                "latitude": float(row.get("Latitude", 0.0)),
                "longitude": float(row.get("Longitude", 0.0)),
                "warning_level_m": float(row.get("Warning_Level", 0.0)),
                "danger_level_m": float(row.get("Danger_Level", 0.0)),
            }
        return {"gauge_id": gid, "full_gauge_id": full_gauge_id(gid)}

    def predict_live(
        self,
        gauge_id: Union[str, int],
        rainfall_history_10d: List[float],
        onset_model_name: str = "RandomForest",
        active_model_name: str = "XGBoost",
    ) -> Dict[str, Any]:
        """
        Run real-time flood risk inference for a specific catchment given 10 daily rainfall values.
        """
        gid = clean_gauge_id(gauge_id)
        if self._static_characteristics is None or gid not in self._static_characteristics.index:
            raise ValueError(f"GaugeID '{gauge_id}' is not in the 20 target Maharashtra Western Ghats catchments.")

        # 1. Compute antecedent features
        antecedent = compute_antecedent_features(rainfall_history_10d)

        # 2. Extract static characteristics
        static_row = self._static_characteristics.loc[[gid]].copy()
        
        # 3. Add station metadata features
        station_info = self.get_station_info(gid)
        static_row["Station"] = station_info.get("station_name", "Unknown")
        static_row["Latitude"] = station_info.get("latitude", 0.0)
        static_row["Longitude"] = station_info.get("longitude", 0.0)
        static_row["River_Name"] = station_info.get("river", "Unknown")
        static_row["Basin"] = station_info.get("basin", "Unknown")
        static_row["State"] = "Maharashtra"
        static_row["Warning_Level"] = station_info.get("warning_level_m", 0.0)
        static_row["Danger_Level"] = station_info.get("danger_level_m", 0.0)
        static_row["Privacy"] = "Open"

        # 4. Merge antecedent features
        for k, v in antecedent.items():
            static_row[k] = v

        # 5. Predict Task A (Onset)
        onset_key = f"task_a_onset_{onset_model_name}"
        if onset_key not in self._models:
            onset_key = "task_a_onset_RandomForest"  # default fallback
        
        onset_bundle = self._models[onset_key]
        onset_model = onset_bundle["model"]
        onset_cols = onset_bundle["feature_cols"]
        onset_thresh = float(onset_bundle["threshold"])

        X_onset = static_row[onset_cols]

        # ---------------------------------------------------------------------
        # MLOps Inference Logging: Telemetry before predict_proba()
        # ---------------------------------------------------------------------
        print(f"\n[PRAVAH ML Pipeline] Ingesting Telemetry for Gauge: {gid} ({station_info.get('station_name', 'Unknown')})")
        print(f"  • Model Architecture : {onset_key}")
        print(f"  • Feature Array Shape: {X_onset.shape} ({X_onset.shape[0]} row, {X_onset.shape[1]} columns)")
        print(f"  • Columns Registered : {list(X_onset.columns)}")
        if "rain_1d" in X_onset.columns:
            print(f"  • Antecedent Profile : 1d={X_onset['rain_1d'].iloc[0]:.1f}mm | 3d={X_onset.get('rain_3d_sum', [0]).iloc[0]:.1f}mm | 7d={X_onset.get('rain_7d_sum', [0]).iloc[0]:.1f}mm | 10d={X_onset.get('rain_10d_sum', [0]).iloc[0]:.1f}mm")

        onset_prob = float(onset_model.predict_proba(X_onset)[0, 1])
        onset_pred = bool(onset_prob >= onset_thresh)
        print(f"  • Predicted Risk     : {onset_prob * 100:.2f}% (Tuned Threshold: {onset_thresh:.4f})\n")

        # 6. Predict Task B (Active)
        active_key = f"task_b_active_{active_model_name}"
        if active_key not in self._models:
            active_key = "task_b_active_XGBoost"  # default fallback
        
        active_bundle = self._models[active_key]
        active_model = active_bundle["model"]
        active_cols = active_bundle["feature_cols"]
        active_thresh = float(active_bundle["threshold"])

        X_active = static_row[active_cols]
        active_prob = float(active_model.predict_proba(X_active)[0, 1])
        active_pred = bool(active_prob >= active_thresh)

        # 7. Alert Tier Calculation
        tier_name, color_code, recommendation = determine_alert_tier(
            onset_prob, onset_thresh, active_prob, active_thresh
        )

        return {
            "station": station_info,
            "prediction_type": "live",
            "alert_tier": {
                "tier": tier_name,
                "color": color_code,
                "recommendation": recommendation,
            },
            "task_a_onset": {
                "model_used": onset_key,
                "probability": round(onset_prob, 4),
                "threshold": round(onset_thresh, 4),
                "is_flood_onset_predicted": onset_pred,
            },
            "task_b_active": {
                "model_used": active_key,
                "probability": round(active_prob, 4),
                "threshold": round(active_thresh, 4),
                "is_active_flood_predicted": active_pred,
            },
            "antecedent_rainfall_summary": {
                "rain_1d_mm": round(antecedent["rain_1d"], 2),
                "rain_3d_sum_mm": round(antecedent["rain_3d_sum"], 2),
                "rain_7d_sum_mm": round(antecedent["rain_7d_sum"], 2),
                "rain_10d_sum_mm": round(antecedent["rain_10d_sum"], 2),
                "rain_3d_max_mm": round(antecedent["rain_3d_max"], 2),
                "rain_7d_max_mm": round(antecedent["rain_7d_max"], 2),
                "dry_days_in_3d": int(antecedent["rain_dry_days_3d"]),
            },
        }

    def predict_historical_date(
        self,
        date_str: str,
        onset_model_name: str = "RandomForest",
        active_model_name: str = "XGBoost",
    ) -> Dict[str, Any]:
        """
        Replay flood predictions across all active catchments for any historical date (1964–2020).
        """
        if self._master_grid is None:
            if MASTER_GRID_PATH.exists():
                logger.info("Loading master daily grid for historical simulation...")
                self._master_grid = pd.read_parquet(MASTER_GRID_PATH)
            else:
                raise FileNotFoundError(f"Master daily grid not found at: {MASTER_GRID_PATH}")

        day_df = self._master_grid[self._master_grid["Date"] == str(date_str)].copy()
        if len(day_df) == 0:
            raise ValueError(f"No records found for date '{date_str}'. Expected date in range 1964-12-01 to 2020-05-27.")

        onset_bundle = self._models.get(f"task_a_onset_{onset_model_name}", self._models["task_a_onset_RandomForest"])
        active_bundle = self._models.get(f"task_b_active_{active_model_name}", self._models["task_b_active_XGBoost"])

        onset_model = onset_bundle["model"]
        onset_cols = onset_bundle["feature_cols"]
        onset_thresh = float(onset_bundle["threshold"])

        active_model = active_bundle["model"]
        active_cols = active_bundle["feature_cols"]
        active_thresh = float(active_bundle["threshold"])

        results = []
        for _, row in day_df.iterrows():
            gid = clean_gauge_id(row["GaugeID"])
            station_info = self.get_station_info(gid)

            X_onset = pd.DataFrame([row[onset_cols].to_dict()])
            onset_prob = float(onset_model.predict_proba(X_onset)[0, 1])
            onset_pred = bool(onset_prob >= onset_thresh)

            X_active = pd.DataFrame([row[active_cols].to_dict()])
            active_prob = float(active_model.predict_proba(X_active)[0, 1])
            active_pred = bool(active_prob >= active_thresh)

            tier_name, color_code, recommendation = determine_alert_tier(
                onset_prob, onset_thresh, active_prob, active_thresh
            )

            actual_onset = int(row.get("target_onset", 0))
            actual_active = int(row.get("target_active", 0))

            results.append({
                "gauge_id": gid,
                "station_name": station_info.get("station_name", "Unknown"),
                "river": station_info.get("river", "Unknown"),
                "latitude": station_info.get("latitude", 0.0),
                "longitude": station_info.get("longitude", 0.0),
                "alert_tier": tier_name,
                "alert_color": color_code,
                "onset_probability": round(onset_prob, 4),
                "onset_predicted": onset_pred,
                "actual_onset_observed": actual_onset,
                "active_probability": round(active_prob, 4),
                "active_predicted": active_pred,
                "actual_active_observed": actual_active,
                "rain_1d_mm": round(float(row.get("rain_1d", 0.0)), 2),
                "rain_3d_sum_mm": round(float(row.get("rain_3d_sum", 0.0)), 2),
                "rain_7d_sum_mm": round(float(row.get("rain_7d_sum", 0.0)), 2),
            })

        return {
            "date": date_str,
            "total_stations_active": len(results),
            "emergency_count": sum(1 for r in results if r["alert_tier"] == "EMERGENCY"),
            "warning_count": sum(1 for r in results if r["alert_tier"] == "WARNING"),
            "advisory_count": sum(1 for r in results if r["alert_tier"] == "ADVISORY"),
            "normal_count": sum(1 for r in results if r["alert_tier"] == "NORMAL"),
            "catchments": results,
        }

    def get_models_summary(self) -> Dict[str, Any]:
        """Return the Phase 3 model evaluation benchmark summary."""
        return self._metrics_summary or {}
