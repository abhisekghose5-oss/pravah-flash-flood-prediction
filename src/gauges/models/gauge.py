"""
PRAVAH — River Gauge Monitoring Data Models & Pydantic Schemas.
Represents real-time hydrometric river levels, warning/danger thresholds,
and temporal trends across monitored catchments.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class RiverGaugeStatus(str, Enum):
    """Categorical hydrological status based on warning/danger thresholds."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    DANGER = "DANGER"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().upper().replace("-", "_").replace(" ", "_")
            for member in cls:
                if member.value == clean or member.name == clean:
                    return member
        return None


class RiverTrend(str, Enum):
    """24-hour rate of water-level stage change."""
    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().upper().replace("-", "_").replace(" ", "_")
            for member in cls:
                if member.value == clean or member.name == clean:
                    return member
        return None


class RiverGaugeHistoryPoint(BaseModel):
    """Single temporal observation in a gauge history time series."""
    timestamp_utc: str
    water_level_m: float
    status: RiverGaugeStatus
    delta_prev_m: float = 0.0


class RiverGauge(BaseModel):
    """Comprehensive river gauge profile and telemetry state."""
    gauge_id: str = Field(..., description="Unique gauge identifier, e.g. 'INDOFLOODS-gauge-684' or '684'")
    clean_id: str = Field(..., description="Stripped numeric ID, e.g. '684'")
    station_name: str = Field(..., description="Name of monitoring station, e.g. 'Karad'")
    river_name: str = Field(..., description="River or major tributary name")
    basin_name: str = Field(..., description="Parent river basin name")
    state: str = Field(default="Maharashtra")
    region: str = Field(default="Maharashtra", description="'Maharashtra' or 'Northeast'")
    latitude: float
    longitude: float
    current_level_m: float
    warning_level_m: float
    danger_level_m: float
    status: RiverGaugeStatus = Field(default=RiverGaugeStatus.NORMAL)
    trend_24h: RiverTrend = Field(default=RiverTrend.STABLE)
    delta_24h_m: float = Field(default=0.0, description="Change in meters over the last 24 hours")
    last_observation_utc: str
    data_source: str = Field(default="Central Water Commission (CWC) & State Hydrology Project")


class RiverGaugeObservationRequest(BaseModel):
    """Payload to submit a live or simulated river-level observation."""
    water_level_m: float = Field(..., description="Observed river stage in meters", ge=0.0, le=1000.0)
    source: Optional[str] = Field("MANUAL_TELEMETRY", description="Data source attribution")
    timestamp_utc: Optional[str] = Field(None, description="ISO UTC timestamp; defaults to now")

    @model_validator(mode='before')
    @classmethod
    def check_level_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "water_level_m" not in d or d["water_level_m"] is None:
                for k in ("water_level", "level", "stage_m", "level_m", "stage"):
                    if k in d and d[k] is not None:
                        d["water_level_m"] = float(d[k])
                        break
            return d
        return data


class ThresholdEvaluationResult(BaseModel):
    """Evaluation of gauge water level against warning and danger thresholds."""
    gauge_id: str
    station_name: str
    river_name: str
    current_level_m: float
    warning_level_m: float
    danger_level_m: float
    head_above_warning_m: float = 0.0
    head_above_danger_m: float = 0.0
    threshold_exceeded: bool
    status: RiverGaugeStatus
    alert_severity: Optional[str] = None  # None, WARNING, CRITICAL, or EVACUATION
    action_recommended: str
