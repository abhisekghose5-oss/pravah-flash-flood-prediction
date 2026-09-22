"""Road segment and closure data models."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RoadStatus(str, Enum):
    OPEN = "OPEN"
    PARTIALLY_BLOCKED = "PARTIALLY_BLOCKED"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class RoadSegment(BaseModel):
    id: str = Field(..., description="Unique road segment identifier, e.g. 'RD-101'")
    name: str = Field(..., description="Highway or corridor name, e.g. 'NH-48 Corridor'")
    from_node: str = Field(..., description="Starting intersection node ID")
    to_node: str = Field(..., description="Ending intersection node ID")
    distance_km: float = Field(..., description="Road length in kilometers")
    base_speed_kmh: float = Field(40.0, description="Base travel speed in km/h")
    flood_risk: float = Field(0.0, ge=0.0, le=1.0, description="Flood risk score (0.0 to 1.0)")
    status: RoadStatus = Field(RoadStatus.OPEN, description="Current road accessibility status")
    cause: Optional[str] = Field(None, description="Cause of blockage (e.g. 'Flash flood inundation')")
    coordinates: List[List[float]] = Field(default_factory=list, description="Polyline points [[lat, lng], ...]")
