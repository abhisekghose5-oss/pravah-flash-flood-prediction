from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.schemas import (
    HealthResponse,
    HistoricalDateResponse,
    LivePredictionRequest,
    LivePredictionResponse,
)
from src.inference.predictor import PravahInferenceEngine, clean_gauge_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pravah.api")

REPO_ROOT = Path(__file__).resolve().parents[2]
CATCHMENTS_GEOJSON = REPO_ROOT / "data" / "processed" / "target_catchments.geojson"

# Instantiate engine singleton
engine = PravahInferenceEngine()

app = FastAPI(
    title="PRAVAH — Flash-Flood Early Warning API",
    description=(
        "REST API serving real-time 1-day ahead flash-flood risk inference, "
        "historical event simulation replay, and geospatial catchment intelligence "
        "for the Maharashtra Western Ghats."
    ),
    version="1.0.0",
)

# Enable Production-Grade CORS for WebGL Dashboard (Port 3000) & APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)


@app.get("/", tags=["System"])
def read_root() -> Dict[str, Any]:
    """Base root endpoint confirming API status."""
    return {
        "status": "online",
        "message": "Pravah API is running",
        "docs": "/docs",
        "health": "/api/health",
        "version": "1.0.0",
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
def get_health() -> HealthResponse:
    """Return system health, loaded models, and registered catchments count."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        project="PRAVAH Flash-Flood Prediction System",
        study_region="Maharashtra Western Ghats",
        available_models=engine.available_models,
        total_catchments=len(engine.registered_gauges),
    )


import urllib.request
from datetime import datetime, timezone

@app.get("/api/health", tags=["System"])
def get_live_system_health() -> Dict[str, Any]:
    """
    Live diagnostic check verifying ML models in memory and Open-Meteo API connectivity.
    """
    models_loaded = bool(engine.available_models and len(engine.available_models) > 0)

    data_api_reachable = False
    try:
        ping_url = "https://api.open-meteo.com/v1/forecast?latitude=18.5204&longitude=73.8567&daily=precipitation_sum&forecast_days=1"
        req = urllib.request.Request(ping_url, headers={"User-Agent": "PRAVAH-HealthCheck/2.1"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data_api_reachable = (resp.status == 200)
    except Exception:
        data_api_reachable = False

    return {
        "status": "System Online",
        "model_loaded": models_loaded,
        "data_api_reachable": data_api_reachable,
        "available_models": engine.available_models,
        "total_catchments": len(engine.registered_gauges),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }



@app.get("/api/v1/catchments", tags=["Geospatial"])
def get_catchments_geojson() -> Any:
    """
    Return GeoJSON FeatureCollection of all 20 target Maharashtra Western Ghats catchments
    enriched with station names, river, danger levels, and operational bounds.
    """
    if not CATCHMENTS_GEOJSON.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target catchments GeoJSON file not found on disk."
        )

    with CATCHMENTS_GEOJSON.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    # Enrich features with station metadata
    for feature in data.get("features", []):
        gid = clean_gauge_id(feature.get("properties", {}).get("GaugeID", ""))
        info = engine.get_station_info(gid)
        feature["properties"].update(info)

    return data


@app.get("/api/v1/catchments/{gauge_id}", tags=["Geospatial"])
def get_single_catchment(gauge_id: str) -> Dict[str, Any]:
    """Retrieve station metadata and static characteristics for a single catchment."""
    gid = clean_gauge_id(gauge_id)
    if gid not in engine.registered_gauges:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gauge '{gauge_id}' not found. Available gauges: {engine.registered_gauges}"
        )
    return engine.get_station_info(gid)


@app.post("/api/v1/predict/live", response_model=LivePredictionResponse, tags=["Inference"])
def predict_live_rainfall(request: LivePredictionRequest) -> LivePredictionResponse:
    """
    Predict 1-day ahead flood onset and active flood status given a 10-day daily rainfall sequence.
    """
    try:
        res = engine.predict_live(
            gauge_id=request.gauge_id,
            rainfall_history_10d=request.rainfall_history_10d,
            onset_model_name=request.onset_model or "RandomForest",
            active_model_name=request.active_model or "XGBoost",
        )
        return LivePredictionResponse(status="success", **res)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Live prediction error: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.get("/api/v1/predict/historical/{date}", response_model=HistoricalDateResponse, tags=["Simulation"])
def predict_historical_date(
    date: str,
    onset_model: Optional[str] = Query("RandomForest", description="Onset model (RandomForest/XGBoost/LightGBM)"),
    active_model: Optional[str] = Query("XGBoost", description="Active model (XGBoost/LightGBM/RandomForest)"),
) -> HistoricalDateResponse:
    """
    Replay flood risk predictions across all catchments for any historical date in the observation record (1964–2020).
    """
    try:
        res = engine.predict_historical_date(
            date_str=date,
            onset_model_name=onset_model or "RandomForest",
            active_model_name=active_model or "XGBoost",
        )
        return HistoricalDateResponse(status="success", **res)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Historical simulation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.get("/api/v1/models/summary", tags=["Models"])
def get_models_benchmark_summary() -> Dict[str, Any]:
    """Retrieve comprehensive Phase 3 performance benchmarks and top feature importances."""
    return engine.get_models_summary()


# =============================================================================
# Citizen WhatsApp/SMS Emergency Alerts Subscription (In-Memory Store)
# =============================================================================
from pydantic import BaseModel, Field

class SubscriptionRequest(BaseModel):
    phone_number: str = Field(..., description="Recipient phone number with country code")
    catchment_id: str = Field(..., description="Subscribed catchment zone ID (or 'ALL')")

class SubscriptionResponse(BaseModel):
    status: str
    message: str

# SQLite Persistence Layer Integration
from src.data.db import (
    save_subscription,
    get_all_subscriptions,
    save_sos_report,
    get_all_sos_reports,
)

# Active cache backed by persistent SQLite
active_subscriptions: list[Dict[str, Any]] = get_all_subscriptions()


@app.post("/api/subscribe", response_model=SubscriptionResponse, tags=["Alerts"])
def subscribe_alerts(subscription: SubscriptionRequest) -> SubscriptionResponse:
    """
    Register a user for automated WhatsApp/SMS emergency flash flood alerts.
    Persists to SQLite database to survive process restarts.
    """
    row_id = save_subscription(subscription.phone_number, subscription.catchment_id)
    record = {
        "id": row_id,
        "phone_number": subscription.phone_number,
        "catchment_id": subscription.catchment_id,
    }
    active_subscriptions.insert(0, record)
    logger.info("Registered emergency subscription #%d: %s | Total active: %d", row_id, record, len(active_subscriptions))
    return SubscriptionResponse(
        status="success",
        message="Number registered for alerts."
    )


# =============================================================================
# Crowdsourced Citizen SOS Flood Reports (SQLite Backed)
# =============================================================================
from datetime import datetime, timezone

class CitizenReport(BaseModel):
    latitude: float = Field(..., description="GPS latitude of the reported flood incident")
    longitude: float = Field(..., description="GPS longitude of the reported flood incident")
    severity: str = Field(..., description="Water depth severity: 'ankle_deep', 'knee_deep', 'waist_deep', or 'above_waist_danger'")
    severity_tier: Optional[str] = Field(None, description="Optional alias for severity")
    landmark_notes: Optional[str] = Field(None, description="Optional landmark or situation details")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Auto-generated ISO 8601 UTC timestamp"
    )

class ReportResponse(BaseModel):
    status: str
    message: str
    report_id: int

# Active cache initialized from SQLite database
active_sos_reports: list[Dict[str, Any]] = get_all_sos_reports()


@app.post("/api/report-flood", response_model=ReportResponse, tags=["Citizen SOS"])
def report_flood(report: CitizenReport) -> ReportResponse:
    """
    Accepts crowdsourced flood reports from citizens and emergency responders.
    Persists the report to SQLite database and logs telemetry for incident dispatch.
    """
    row_id = save_sos_report(
        latitude=report.latitude,
        longitude=report.longitude,
        severity=report.severity,
        severity_tier=report.severity_tier,
        landmark_notes=report.landmark_notes,
        timestamp=report.timestamp,
    )

    report_dict = report.model_dump() if hasattr(report, "model_dump") else report.dict()
    report_dict["id"] = row_id
    active_sos_reports.append(report_dict)

    logger.info("🚨 New Citizen SOS Report #%d: Lat %.4f, Lng %.4f, Severity: %s (Persisted to SQLite)", 
                row_id, report.latitude, report.longitude, report.severity)

    return ReportResponse(
        status="success",
        message="SOS report received and dispatched to emergency controllers.",
        report_id=row_id
    )


@app.get("/api/reports", response_model=list[Dict[str, Any]], tags=["Citizen SOS"])
def get_all_reports() -> list[Dict[str, Any]]:
    """
    Returns the list of active crowdsourced flood reports from SQLite
    for frontend map rendering and spatial telemetry.
    """
    return get_all_sos_reports()


# =============================================================================
# Evacuation Safe Zones & Nearest Relief Shelter Telemetry
# =============================================================================
import math

RELIEF_CAMPS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Shivaji Nagar Elevated Disaster Shelter",
        "latitude": 18.5312,
        "longitude": 73.8445,
        "capacity": 650,
        "type": "Elevated Shelter",
    },
    {
        "id": 2,
        "name": "Sinhagad Road Government Higher Secondary School",
        "latitude": 18.4789,
        "longitude": 73.8192,
        "capacity": 500,
        "type": "Government School",
    },
    {
        "id": 3,
        "name": "Lonavala High Ground Emergency Refuge Center",
        "latitude": 18.7557,
        "longitude": 73.4091,
        "capacity": 1200,
        "type": "Elevated Shelter",
    },
    {
        "id": 4,
        "name": "Panchganga Zilla Parishad Model School",
        "latitude": 18.3842,
        "longitude": 73.8567,
        "capacity": 450,
        "type": "Government School",
    },
]


def calculate_nearest_camp(lat: float, lng: float) -> tuple[Dict[str, Any], float]:
    """
    Computes the shortest great-circle distance between a given GPS coordinate
    and all registered relief camps using the spherical Haversine formula.
    """
    if not RELIEF_CAMPS:
        raise ValueError("No relief camps are currently registered.")

    earth_radius_km = 6371.0
    user_lat_rad = math.radians(lat)
    user_lng_rad = math.radians(lng)

    closest_camp = None
    min_dist_km = float("inf")

    for camp in RELIEF_CAMPS:
        camp_lat_rad = math.radians(camp["latitude"])
        camp_lng_rad = math.radians(camp["longitude"])

        dlat = camp_lat_rad - user_lat_rad
        dlng = camp_lng_rad - user_lng_rad

        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(user_lat_rad)
            * math.cos(camp_lat_rad)
            * math.sin(dlng / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        dist_km = earth_radius_km * c

        if dist_km < min_dist_km:
            min_dist_km = dist_km
            closest_camp = camp

    return closest_camp, round(min_dist_km, 2)


@app.get("/api/safe-zones", response_model=List[Dict[str, Any]], tags=["Evacuation"])
def get_safe_zones() -> List[Dict[str, Any]]:
    """
    Retrieve the directory of all operational disaster relief shelters,
    elevated refuges, and emergency staging schools.
    """
    return RELIEF_CAMPS


@app.get("/api/evacuation-route", tags=["Evacuation"])
def get_evacuation_route(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Current GPS Latitude"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="Current GPS Longitude"),
) -> Dict[str, Any]:
    """
    Calculates the closest relief camp to the citizen's current GPS location
    and returns routing telemetry and distance in kilometers.
    """
    try:
        nearest_camp, distance_km = calculate_nearest_camp(lat, lng)
        return {
            "status": "success",
            "user_location": {"latitude": lat, "longitude": lng},
            "nearest_camp": nearest_camp,
            "distance_km": distance_km,
            "estimated_walk_time_mins": int(distance_km * 12),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to calculate evacuation route: {str(exc)}",
        )



