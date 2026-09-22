"""Evacuation routing request and response models."""
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, model_validator


class RouteObjective(str, Enum):
    FASTEST = "FASTEST"
    LOWEST_RISK = "LOWEST_RISK"
    NEAREST_SHELTER = "NEAREST_SHELTER"
    BALANCED = "BALANCED"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().upper().replace("-", "_").replace(" ", "_")
            for member in cls:
                if member.value == clean or member.name == clean:
                    return member
        return None


class RoutingAlgorithm(str, Enum):
    ASTAR = "ASTAR"
    DIJKSTRA = "DIJKSTRA"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().upper().replace("-", "_").replace(" ", "_")
            for member in cls:
                if member.value == clean or member.name == clean:
                    return member
        return None


class SafetyClassification(str, Enum):
    LOW_RISK = "LOW_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    HIGH_RISK = "HIGH_RISK"
    UNSAFE = "UNSAFE"
    NO_SAFE_ROUTE_AVAILABLE = "NO_SAFE_ROUTE_AVAILABLE"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().upper().replace("-", "_").replace(" ", "_")
            for member in cls:
                if member.value == clean or member.name == clean:
                    return member
        return None


class RouteRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Evacuation start latitude", examples=[18.5204])
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Evacuation start longitude", examples=[73.8567])
    destination_shelter_id: Optional[str] = Field(None, description="Optional target shelter ID (defaults to optimal)")
    objective: RouteObjective = Field(RouteObjective.BALANCED, description="Routing goal: FASTEST, LOWEST_RISK, NEAREST_SHELTER, BALANCED")
    algorithm: RoutingAlgorithm = Field(RoutingAlgorithm.ASTAR, description="Pathfinding algorithm: ASTAR or DIJKSTRA")
    travel_mode: str = Field("VEHICLE", description="Transit mode: VEHICLE or WALKING")

    @model_validator(mode='before')
    @classmethod
    def check_coordinate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "latitude" not in d or d["latitude"] is None:
                for k in ("lat", "origin_lat", "start_lat", "origin_latitude"):
                    if k in d and d[k] is not None:
                        d["latitude"] = float(d[k])
                        break
            if "longitude" not in d or d["longitude"] is None:
                for k in ("lng", "lon", "origin_lng", "origin_lon", "start_lng", "origin_longitude"):
                    if k in d and d[k] is not None:
                        d["longitude"] = float(d[k])
                        break
            return d
        return data


class Waypoint(BaseModel):
    node_id: str
    name: str
    latitude: float
    longitude: float
    cumulative_distance_km: float
    cumulative_time_mins: float
    risk_score: float


class EvacuationRoute(BaseModel):
    route_id: str = Field(..., description="Unique route code, e.g. 'EVAC-1024'")
    origin: Dict[str, float] = Field(..., description="Start location {'latitude': ..., 'longitude': ...}")
    destination: Dict[str, Any] = Field(..., description="Target shelter details")
    distance_km: float = Field(..., description="Total route distance in km")
    estimated_time_minutes: float = Field(..., description="Total travel time estimate with delays")
    base_time_minutes: float = Field(..., description="Uncongested baseline transit time")
    flood_delay_minutes: float = Field(..., description="Delay caused by water hazard slows")
    road_delay_minutes: float = Field(..., description="Delay caused by partial obstructions")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Cumulative flood risk score")
    safety_classification: SafetyClassification = Field(..., description="Safety tier: LOW_RISK, MODERATE_RISK, HIGH_RISK, UNSAFE")
    algorithm_used: RoutingAlgorithm = Field(..., description="ASTAR or DIJKSTRA")
    objective: RouteObjective = Field(..., description="FASTEST, LOWEST_RISK, NEAREST_SHELTER, or BALANCED")
    polyline: List[List[float]] = Field(..., description="Route coordinates [[lat, lng], ...]")
    waypoints: List[Waypoint] = Field(default_factory=list, description="Step-by-step corridor waypoints")
    road_closures_avoided: int = Field(0, description="Count of closed road segments successfully bypassed")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvacuationPlanResponse(BaseModel):
    status: str = Field(..., description="'success' or 'no_safe_route'")
    message: str = Field(..., description="Operational advisory or evacuation directive")
    primary_route: Optional[EvacuationRoute] = None
    alternative_routes: List[EvacuationRoute] = Field(default_factory=list)
    available_shelters_count: int = 0
    active_closures_count: int = 0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
