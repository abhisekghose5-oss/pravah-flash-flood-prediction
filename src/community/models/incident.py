"""
PRAVAH — Community Incident Data Models & Pydantic Schemas
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    FLOOD_OBSERVATION = "FLOOD_OBSERVATION"
    BLOCKED_ROAD = "BLOCKED_ROAD"
    WATER_LEVEL = "WATER_LEVEL"
    GENERAL_INCIDENT = "GENERAL_INCIDENT"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RoadStatus(str, Enum):
    OPEN = "OPEN"
    PARTIALLY_BLOCKED = "PARTIALLY_BLOCKED"
    COMPLETELY_BLOCKED = "COMPLETELY_BLOCKED"
    UNKNOWN = "UNKNOWN"


class ReportStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"


class CommunityReportCreate(BaseModel):
    """Payload schema for submitting a new community flood report."""
    report_type: ReportType = Field(
        ...,
        description="Category of the report (FLOOD_OBSERVATION, BLOCKED_ROAD, WATER_LEVEL, GENERAL_INCIDENT)",
        examples=["FLOOD_OBSERVATION"]
    )
    description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Detailed description of the observed flood condition or hazard",
        examples=["Water is rising rapidly across the main market square. Road submerged."]
    )
    severity: SeverityLevel = Field(
        default=SeverityLevel.MODERATE,
        description="Citizen-reported severity level (LOW, MODERATE, HIGH, CRITICAL)",
        examples=["HIGH"]
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="GPS latitude coordinate of the observation",
        examples=[18.5204]
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="GPS longitude coordinate of the observation",
        examples=[73.8567]
    )
    location_accuracy: Optional[float] = Field(
        None,
        ge=0.0,
        description="GPS location accuracy radius in meters if provided by device",
        examples=[12.5]
    )
    location_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Human-readable town, village, or landmark name",
        examples=["Panchgani Valley Road"]
    )
    district: Optional[str] = Field(
        None,
        max_length=100,
        description="Administrative district",
        examples=["Satara"]
    )
    state_region: Optional[str] = Field(
        None,
        max_length=100,
        description="State or geographic region (e.g. Maharashtra, Northeast)",
        examples=["Maharashtra"]
    )
    water_depth: Optional[float] = Field(
        None,
        ge=0.0,
        le=50.0,
        description="Observed approximate water depth in meters",
        examples=[1.2]
    )
    road_status: Optional[RoadStatus] = Field(
        None,
        description="Road passability status if reporting a road hazard",
        examples=["COMPLETELY_BLOCKED"]
    )
    road_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Road or highway identifier (e.g., NH-48, State Highway 12)",
        examples=["NH-48"]
    )
    hazard_cause: Optional[str] = Field(
        None,
        max_length=100,
        description="Cause of hazard (e.g., Flooding, Landslide, Debris, Fallen Trees)",
        examples=["Flooding"]
    )
    reporter_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional reporter display name (masked in public responses)",
        examples=["Rohit K."]
    )
    reporter_contact: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional emergency contact/phone number (strictly masked/hidden)",
        examples=["+919876543210"]
    )
    timestamp: Optional[str] = Field(
        None,
        description="ISO 8601 UTC timestamp of observation"
    )


class StatusUpdatePayload(BaseModel):
    """Payload schema for moderating an existing community report."""
    verification_status: ReportStatus = Field(
        ...,
        description="Target status (PENDING_REVIEW, VERIFIED, REJECTED, RESOLVED)",
        examples=["VERIFIED"]
    )
    moderator_notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional note from emergency dispatcher or moderator explaining action",
        examples=["Confirmed with local police station dispatch."]
    )


class CommunityReportResponse(BaseModel):
    """Standardized response schema for a community report."""
    id: int
    report_code: str
    report_type: str
    title: Optional[str] = None
    description: str
    severity: str
    latitude: float
    longitude: float
    location_accuracy: Optional[float] = None
    location_name: Optional[str] = None
    district: Optional[str] = None
    state_region: Optional[str] = None
    water_depth: Optional[float] = None
    road_status: Optional[str] = None
    road_name: Optional[str] = None
    hazard_cause: Optional[str] = None
    photo_url: Optional[str] = None
    additional_photos: List[str] = Field(default_factory=list)
    reported_at: str
    verification_status: str
    is_verified: bool
    is_duplicate: bool = False
    parent_incident_id: Optional[int] = None
    cluster_count: int = 1
    reporter_display: str = "Citizen Reporter"
    moderator_notes: Optional[str] = None
    created_at: str
    updated_at: str


class CommunityStatsResponse(BaseModel):
    """Aggregate statistics for the Community Reports Dashboard."""
    total_reports: int
    reports_today: int
    pending_verification: int
    verified_reports: int
    blocked_roads: int
    active_incidents: int
    timestamp: str


class IncidentClusterResponse(BaseModel):
    """Grouped incident cluster with associated child reports."""
    cluster_id: int
    primary_code: str
    report_type: str
    severity: str
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    child_count: int
    latest_reported_at: str
    reports: List[Dict[str, Any]] = Field(default_factory=list)
