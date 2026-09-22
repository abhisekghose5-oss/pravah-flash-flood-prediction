"""Shelter and relief center models."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ShelterStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    NEAR_CAPACITY = "NEAR_CAPACITY"
    FULL = "FULL"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class Shelter(BaseModel):
    id: str = Field(..., description="Unique shelter identifier, e.g. 'SH-101'")
    name: str = Field(..., description="Public name of relief shelter")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    capacity: int = Field(500, description="Total maximum bed/refuge capacity")
    current_occupancy: int = Field(0, description="Current registered evacuees")
    status: ShelterStatus = Field(ShelterStatus.AVAILABLE, description="Operational status")
    shelter_type: str = Field("Elevated Shelter", description="Type (e.g. Elevated School, Community Hall)")
    region: str = Field("Maharashtra", description="State or basin region")
    district: Optional[str] = Field(None, description="Administrative district")
    contact: Optional[str] = Field(None, description="Emergency dispatch / camp contact hotline")
    accessibility_notes: Optional[str] = Field(None, description="Disability / medical ramp accessibility")

    @property
    def is_accepting_evacuees(self) -> bool:
        """Returns True if shelter can receive evacuees (not FULL and not CLOSED)."""
        return self.status in (ShelterStatus.AVAILABLE, ShelterStatus.NEAR_CAPACITY)
