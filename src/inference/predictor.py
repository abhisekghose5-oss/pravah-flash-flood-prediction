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
SOIL_PATH = PROCESSED_DIR / "soil_hydrology_features.csv"
RIVER_LEVEL_PATH = PROCESSED_DIR / "river_level_telemetry.csv"
DAMS_PATH = PROCESSED_DIR / "dams_reservoirs.csv"
TERRAIN_PATH = PROCESSED_DIR / "mountain_terrain_features.csv"

NE_PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "northeast"
NE_STATION_CATALOG_PATH = NE_PROCESSED_DIR / "station_catalog.csv"
NE_STATIC_PATH = NE_PROCESSED_DIR / "northeast_candidate_static_features.csv"
NE_THRESHOLDS_PATH = MODELS_DIR / "thresholds_ne.json"
NE_METRICS_PATH = NE_PROCESSED_DIR / "ne_evaluation_metrics.json"
NE_CATCHMENTS_GEOJSON = NE_PROCESSED_DIR / "northeast_candidate_catchments.geojson"

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
        self._soil_data: Optional[pd.DataFrame] = None
        self._river_level_data: Optional[pd.DataFrame] = None
        self._dams_data: Optional[pd.DataFrame] = None
        self._terrain_data: Optional[pd.DataFrame] = None

        # Northeast State Containers
        self._ne_station_catalog: Optional[pd.DataFrame] = None
        self._ne_static_characteristics: Optional[pd.DataFrame] = None
        self._ne_thresholds: Dict[str, Any] = {}
        self._ne_metrics: Dict[str, Any] = {}

        self._load_metadata()
        self._load_models()

    def _load_metadata(self) -> None:
        """Load and index static catchment characteristics and station metadata."""
        if CHARACTERISTICS_PATH.exists():
            chars = pd.read_csv(CHARACTERISTICS_PATH)
            chars = chars.copy().assign(clean_gauge_id=chars["GaugeID"].map(clean_gauge_id))
            self._static_characteristics = chars.set_index("clean_gauge_id")
            logger.info("Loaded static characteristics for %d catchments", len(self._static_characteristics))

        if METADATA_PATH.exists():
            meta = pd.read_csv(METADATA_PATH)
            meta = meta.copy().assign(clean_gauge_id=meta["GaugeID"].map(clean_gauge_id))
            self._station_metadata = meta.set_index("clean_gauge_id")
            logger.info("Loaded station metadata for %d gauges", len(self._station_metadata))

        if METRICS_PATH.exists():
            with METRICS_PATH.open("r", encoding="utf-8") as fh:
                self._metrics_summary = json.load(fh)

        # Load Northeast Metadata
        if NE_STATION_CATALOG_PATH.exists():
            try:
                ne_cat = pd.read_csv(NE_STATION_CATALOG_PATH)
                self._ne_station_catalog = ne_cat.set_index("StationID")
                logger.info("Loaded Northeast station catalog for %d stations", len(self._ne_station_catalog))
            except Exception as e:
                logger.warning("Failed to load NE station catalog: %s", e)

        if NE_STATIC_PATH.exists():
            try:
                self._ne_static_characteristics = pd.read_csv(NE_STATIC_PATH).drop_duplicates(subset=["StationID"]).set_index("StationID")
            except Exception as e:
                logger.warning("Failed to load NE static characteristics: %s", e)

        if NE_THRESHOLDS_PATH.exists():
            try:
                with NE_THRESHOLDS_PATH.open("r", encoding="utf-8") as fh:
                    self._ne_thresholds = json.load(fh)
            except Exception as e:
                logger.warning("Failed to load NE thresholds: %s", e)

        if NE_METRICS_PATH.exists():
            try:
                with NE_METRICS_PATH.open("r", encoding="utf-8") as fh:
                    self._ne_metrics = json.load(fh)
            except Exception as e:
                logger.warning("Failed to load NE metrics: %s", e)
        if SOIL_PATH.exists():
            soil = pd.read_csv(SOIL_PATH)
            soil = soil.assign(clean_gauge_id=soil["GaugeID"].map(clean_gauge_id))
            self._soil_data = soil.set_index("clean_gauge_id")

        if RIVER_LEVEL_PATH.exists():
            rlevel = pd.read_csv(RIVER_LEVEL_PATH)
            rlevel = rlevel.assign(clean_gauge_id=rlevel["GaugeID"].map(clean_gauge_id))
            self._river_level_data = rlevel

        if DAMS_PATH.exists():
            dams = pd.read_csv(DAMS_PATH)
            dams = dams.assign(clean_gauge_id=dams["downstream_gauge_id"].map(clean_gauge_id))
            self._dams_data = dams

        if TERRAIN_PATH.exists():
            terr = pd.read_csv(TERRAIN_PATH)
            terr = terr.assign(clean_gauge_id=terr["GaugeID"].map(clean_gauge_id))
            self._terrain_data = terr.set_index("clean_gauge_id")

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

    @property
    def registered_ne_stations(self) -> List[str]:
        if self._ne_station_catalog is not None:
            return sorted(self._ne_station_catalog.index.tolist())
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
                "state": "Maharashtra",
                "region": "Maharashtra",
            }
        return {"gauge_id": gid, "full_gauge_id": full_gauge_id(gid), "region": "Maharashtra"}

    def get_ne_station_info(self, station_id: Union[str, int]) -> Dict[str, Any]:
        """Retrieve static station metadata for a Northeast monitoring station."""
        st = str(station_id).strip()
        if self._ne_station_catalog is not None and st in self._ne_station_catalog.index:
            row = self._ne_station_catalog.loc[st]
            lat = float(row.get("Latitude", 26.2))
            lng = float(row.get("Longitude", 92.5))
            return {
                "gauge_id": st,
                "full_gauge_id": f"NE-{st}",
                "name": st,
                "station_name": st,
                "river": "Brahmaputra / Tributary",
                "basin": "Brahmaputra",
                "lat": lat,
                "lng": lng,
                "latitude": lat,
                "longitude": lng,
                "warning_level_m": 0.0,
                "danger_level_m": 0.0,
                "state": str(row.get("State", "Assam")),
                "district": str(row.get("District", "Unknown")).title(),
                "region": "Northeast",
            }
        return {
            "gauge_id": st,
            "full_gauge_id": f"NE-{st}",
            "name": st,
            "station_name": st,
            "river": "Brahmaputra / Tributary",
            "basin": "Brahmaputra",
            "lat": 26.2,
            "lng": 92.5,
            "latitude": 26.2,
            "longitude": 92.5,
            "warning_level_m": 0.0,
            "danger_level_m": 0.0,
            "state": "Assam",
            "district": "Unknown",
            "region": "Northeast",
        }

    def predict_live_ne(
        self,
        station_id: Union[str, int],
        rainfall_history_10d: List[float],
        onset_model_name: str = "XGBoost",
        active_model_name: str = "XGBoost",
    ) -> Dict[str, Any]:
        """
        Run real-time flood risk inference for a Northeast catchment station
        given 10 daily rainfall values using trained Northeast models and calibrated CSI thresholds.
        """
        st = str(station_id).strip()
        station_info = self.get_ne_station_info(st)

        antecedent = compute_antecedent_features(rainfall_history_10d)

        # Static defaults and terrain interaction
        slope = 0.052
        rain_1d = antecedent["rain_1d"]
        rain_3d_sum = antecedent["rain_3d_sum"]

        static_attrs = {
            "basin_area_km2": 250.0,
            "upstream_area_km2": 1500.0,
            "ORDER": 3,
            "DIST_MAIN": 35000.0,
            "DIST_SINK": 35000.0,
            "Drainage Area": 250.0,
            "Downvalley Length": 35000.0,
            "Stream Order": 3,
            "slope": slope,
            "rain_1d_x_slope": rain_1d * slope,
            "rain_3d_x_slope": rain_3d_sum * slope,
            "rainfall_mm": rain_1d,
        }
        if self._ne_static_characteristics is not None and st in self._ne_static_characteristics.index:
            s_row = self._ne_static_characteristics.loc[st]
            if isinstance(s_row, pd.DataFrame):
                s_row = s_row.iloc[0]
            static_attrs["basin_area_km2"] = float(s_row.get("basin_area_km2", 250.0) or 250.0)
            static_attrs["upstream_area_km2"] = float(s_row.get("upstream_area_km2", 1500.0) or 1500.0)
            static_attrs["ORDER"] = int(s_row.get("ORDER", 3) or 3)
            static_attrs["DIST_MAIN"] = float(s_row.get("DIST_MAIN", 35000.0) or 35000.0)
            static_attrs["DIST_SINK"] = float(s_row.get("DIST_SINK", 35000.0) or 35000.0)
            static_attrs["Drainage Area"] = static_attrs["basin_area_km2"]
            static_attrs["Downvalley Length"] = static_attrs["DIST_MAIN"]
            static_attrs["Stream Order"] = static_attrs["ORDER"]

        feature_dict = {**antecedent, **static_attrs}
        input_row = pd.DataFrame([feature_dict])

        # Resolve model bundles
        norm_onset = onset_model_name.lower()
        if "lightgbm" in norm_onset or "lgbm" in norm_onset:
            onset_key = "lgbm_task_a_ne"
            model_key_name = "LightGBM"
        elif "randomforest" in norm_onset or "rf" in norm_onset:
            onset_key = "rf_task_a_ne"
            model_key_name = "RandomForest"
        else:
            onset_key = "xgb_task_a_ne"
            model_key_name = "XGBoost"

        if onset_key not in self._models:
            onset_key = "xgb_task_a_ne"
            model_key_name = "XGBoost"

        onset_bundle = self._models[onset_key]
        onset_model = onset_bundle["model"]
        onset_cols = onset_bundle["feature_cols"]
        onset_thresh = float(self._ne_thresholds.get("task_a_onset_ne", {}).get(model_key_name, onset_bundle.get("threshold", 0.05)))

        for c in onset_cols:
            if c not in input_row.columns:
                input_row[c] = 0.0

        X_onset = input_row[onset_cols]
        onset_prob = float(onset_model.predict_proba(X_onset)[0, 1])
        if antecedent["rain_10d_sum"] <= 0.0:
            onset_prob = 0.0
        onset_pred = bool(onset_prob >= onset_thresh)

        norm_active = active_model_name.lower()
        if "lightgbm" in norm_active or "lgbm" in norm_active:
            active_key = "lgbm_task_b_ne"
            active_model_key = "LightGBM"
        elif "randomforest" in norm_active or "rf" in norm_active:
            active_key = "rf_task_b_ne"
            active_model_key = "RandomForest"
        else:
            active_key = "xgb_task_b_ne"
            active_model_key = "XGBoost"

        if active_key not in self._models:
            active_key = "xgb_task_b_ne"
            active_model_key = "XGBoost"

        active_bundle = self._models[active_key]
        active_model = active_bundle["model"]
        active_cols = active_bundle["feature_cols"]
        active_thresh = float(self._ne_thresholds.get("task_b_active_ne", {}).get(active_model_key, active_bundle.get("threshold", 0.49)))

        for c in active_cols:
            if c not in input_row.columns:
                input_row[c] = 0.0

        X_active = input_row[active_cols]
        active_prob = float(active_model.predict_proba(X_active)[0, 1])
        if antecedent["rain_10d_sum"] <= 0.0:
            active_prob = 0.0
        active_pred = bool(active_prob >= active_thresh)

        # 4-Tier Early Warning Calibration
        rain_3d = float(antecedent.get("rain_3d_sum", 0.0))
        if (active_prob >= active_thresh and onset_prob >= onset_thresh) or (active_prob >= 0.70) or (onset_prob >= onset_thresh and rain_3d > 120.0):
            tier_name = "EMERGENCY"
            color_code = "RED"
            recommendation = "Severe flash flood threshold reached in Northeast catchment. Activate SDRF/NDRF emergency evacuation."
        elif (active_prob >= active_thresh) or (onset_prob >= onset_thresh and rain_3d > 60.0):
            tier_name = "SEVERE"
            color_code = "ORANGE"
            recommendation = "High probability of flood onset or sustained inundation in Brahmaputra tributary. Alert riverine settlements."
        elif (active_prob >= 0.5 * active_thresh) or (onset_prob >= onset_thresh and rain_3d > 30.0) or (rain_3d > 40.0):
            tier_name = "ADVISORY"
            color_code = "YELLOW"
            recommendation = "Moderate antecedent saturation in hill catchment. Monitor river gauge telemetry closely."
        else:
            tier_name = "NORMAL"
            color_code = "GREEN"
            recommendation = "Hydrological conditions within safe baseline limits."

        return {
            "station": station_info,
            "region": "Northeast",
            "is_northeast": True,
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

    def get_ne_models_summary(self) -> Dict[str, Any]:
        """Return Northeast model evaluation benchmarks and CSI scores."""
        res = dict(self._ne_metrics or {})
        if "task_a_onset_ne" in res and "task_a_onset" not in res:
            res["task_a_onset"] = res["task_a_onset_ne"]
        if "task_b_active_ne" in res and "task_b_active" not in res:
            res["task_b_active"] = res["task_b_active_ne"]
        
        res["thresholds"] = {
            "task_a_onset": (self._ne_thresholds or {}).get("task_a_onset_ne", {}),
            "task_b_active": (self._ne_thresholds or {}).get("task_b_active_ne", {}),
            **(self._ne_thresholds or {}),
        }
        return res

    def get_hydrological_context(self, gauge_id: Union[str, int]) -> Dict[str, Any]:
        """Retrieve enriched physical context: soil, river stage, upstream dam, terrain."""
        gid = clean_gauge_id(gauge_id)
        ctx: Dict[str, Any] = {}

        if self._soil_data is not None and gid in self._soil_data.index:
            row = self._soil_data.loc[gid]
            ctx["soil"] = {
                "soil_order": str(row.get("soil_order", "")),
                "soil_texture": str(row.get("soil_texture_class", "")),
                "ksat_mm_hr": float(row.get("saturated_hydraulic_conductivity_ksat_mm_hr", 0.0)),
                "hydrologic_group": str(row.get("hydrologic_soil_group", "")),
                "scs_curve_number": int(row.get("scs_curve_number_cn2", 0)),
                "available_water_capacity_mm_m": float(row.get("available_water_capacity_awc_mm_m", 0.0)),
            }

        if self._river_level_data is not None:
            matches = self._river_level_data[self._river_level_data["clean_gauge_id"] == gid]
            if not matches.empty:
                latest = matches.iloc[-1]
                ctx["river_stage"] = {
                    "water_level_m": float(latest.get("water_level_m", 0.0)),
                    "warning_level_m": float(latest.get("warning_level_m", 0.0)),
                    "danger_level_m": float(latest.get("danger_level_m", 0.0)),
                    "freeboard_remaining_m": float(latest.get("freeboard_remaining_m", 0.0)),
                    "stage_status": str(latest.get("stage_status", "NORMAL")),
                    "discharge_cumecs": float(latest.get("discharge_cumecs", 0.0)),
                    "rate_of_rise_m_hr": float(latest.get("rate_of_rise_m_hr", 0.0)),
                }

        if self._dams_data is not None:
            matches = self._dams_data[self._dams_data["clean_gauge_id"] == gid]
            if not matches.empty:
                dam = matches.iloc[0]
                ctx["upstream_dam"] = {
                    "dam_name": str(dam.get("dam_name", "")),
                    "storage_pct": float(dam.get("current_storage_pct", 0.0)),
                    "spillway_outflow_cumecs": float(dam.get("spillway_outflow_cumecs", 0.0)),
                    "gate_status": str(dam.get("gate_opening_status", "")),
                    "distance_km": float(dam.get("distance_to_downstream_gauge_km", 0.0)),
                    "travel_time_hrs": float(dam.get("emergency_release_travel_time_hrs", 0.0)),
                }

        if self._terrain_data is not None and gid in self._terrain_data.index:
            row = self._terrain_data.loc[gid]
            ctx["terrain"] = {
                "mean_elevation_m": float(row.get("mean_elevation_m", 0.0)),
                "catchment_relief_m": float(row.get("catchment_relief_m", 0.0)),
                "mean_slope_deg": float(row.get("mean_slope_degrees", 0.0)),
                "steep_slope_area_fraction": float(row.get("steep_slope_area_fraction", 0.0)),
                "twi": float(row.get("topographic_wetness_index_twi", 0.0)),
                "dominant_relief_type": str(row.get("dominant_relief_type", "")),
            }

        return ctx

    def predict_live(
        self,
        gauge_id: Union[str, int],
        rainfall_history_10d: List[float],
        onset_model_name: str = "RandomForest",
        active_model_name: str = "XGBoost",
        region: Optional[str] = "maharashtra",
    ) -> Dict[str, Any]:
        """
        Run real-time flood risk inference for a specific catchment given 10 daily rainfall values.
        Routes to Northeast model if region is 'NE' or gauge_id is in registered Northeast stations.
        """
        target_region = str(region or "maharashtra").strip().upper()
        if target_region in ["NE", "NORTHEAST"] or str(gauge_id) in self.registered_ne_stations:
            return self.predict_live_ne(
                station_id=gauge_id,
                rainfall_history_10d=rainfall_history_10d,
                onset_model_name=onset_model_name,
                active_model_name=active_model_name,
            )

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
            "hydrological_context": self.get_hydrological_context(gid),
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
