"""Flood risk zone models."""
from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class RiskZone(BaseModel):
    zone_id: str = Field(..., description="Risk zone identifier, e.g. 'ZONE-MULA-01'")
    name: str = Field(..., description="Descriptive zone name, e.g. 'Mula-Mutha Confluence Lowlands'")
    basin: str = Field(..., description="River basin name")
    risk_level: RiskLevel = Field(RiskLevel.LOW, description="Categorical risk tier")
    risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Numerical flood risk score")
    inundation_depth_m: float = Field(0.0, description="Estimated floodwater depth in meters")
    polygon: List[List[float]] = Field(default_factory=list, description="Boundary polygon [[lat, lng], ...]")
