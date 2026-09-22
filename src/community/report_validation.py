"""
PRAVAH — Community Report Validation Service
Performs domain validation, coordinate verification, XSS sanitization,
and schema integrity enforcement on incoming citizen flood observations.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Tuple
from fastapi import HTTPException

from src.community.models.incident import (
    CommunityReportCreate,
    ReportType,
    RoadStatus,
    SeverityLevel,
)
from src.community.utils.helpers import get_current_utc_iso, sanitize_text


def validate_coordinates(lat: float, lon: float) -> None:
    """Validate latitude and longitude ranges and detect illegal values."""
    if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
        raise HTTPException(
            status_code=422,
            detail="Invalid GPS coordinates: latitude and longitude must be finite real numbers."
        )

    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(
            status_code=422,
            detail=f"Latitude {lat} is out of bounds (must be between -90.0 and +90.0)."
        )

    if not (-180.0 <= lon <= 180.0):
        raise HTTPException(
            status_code=422,
            detail=f"Longitude {lon} is out of bounds (must be between -180.0 and +180.0)."
        )

    # Null Island check (0.0, 0.0)
    if abs(lat) < 1e-6 and abs(lon) < 1e-6:
        raise HTTPException(
            status_code=422,
            detail="Invalid coordinates: (0, 0) Null Island location detected. Please supply valid geographic coordinates."
        )


def infer_region_tag(lat: float, lon: float) -> str:
    """Infer PRAVAH operational basin from coordinates."""
    is_ne = (23.5 <= lat <= 29.5 and 88.5 <= lon <= 98.0)
    is_mh = (15.0 <= lat <= 22.5 and 72.0 <= lon <= 81.0)
    if is_ne:
        return "Northeast"
    elif is_mh:
        return "Maharashtra"
    elif 8.0 <= lat <= 37.0 and 68.0 <= lon <= 97.5:
        return "India (National)"
    return "Other"


def validate_and_clean_report_data(payload: CommunityReportCreate) -> Dict[str, Any]:
    """
    Validates report fields according to report type, sanitizes strings,
    and returns a clean dictionary ready for database persistence.
    """
    # 1. Coordinates check
    validate_coordinates(payload.latitude, payload.longitude)

    # 2. Text sanitization
    clean_desc = sanitize_text(payload.description, max_length=2000)
    if len(clean_desc) < 3:
        raise HTTPException(
            status_code=422,
            detail="Report description must contain at least 3 valid characters."
        )

    clean_location = sanitize_text(payload.location_name, max_length=255) if payload.location_name else None
    clean_district = sanitize_text(payload.district, max_length=100) if payload.district else None
    clean_road_name = sanitize_text(payload.road_name, max_length=255) if payload.road_name else None
    clean_hazard_cause = sanitize_text(payload.hazard_cause, max_length=100) if payload.hazard_cause else None
    clean_reporter_name = sanitize_text(payload.reporter_name, max_length=100) if payload.reporter_name else None
    clean_reporter_contact = sanitize_text(payload.reporter_contact, max_length=100) if payload.reporter_contact else None

    # 3. Report-type specific checks
    road_status = payload.road_status
    if payload.report_type == ReportType.BLOCKED_ROAD:
        if road_status is None:
            road_status = RoadStatus.PARTIALLY_BLOCKED
        if not clean_hazard_cause:
            clean_hazard_cause = "Flooding / Road Blockage"

    water_depth = payload.water_depth
    if payload.report_type == ReportType.WATER_LEVEL and water_depth is None:
        # Default estimation if not provided in water level report
        water_depth = 0.5

    # 4. Region inference
    inferred_region = payload.state_region or infer_region_tag(payload.latitude, payload.longitude)

    # 5. Timestamp validation
    reported_at = payload.timestamp
    if reported_at:
        try:
            # Parse ISO timestamp to ensure validity
            datetime.fromisoformat(reported_at.replace("Z", "+00:00"))
        except Exception:
            reported_at = get_current_utc_iso()
    else:
        reported_at = get_current_utc_iso()

    return {
        "report_type": payload.report_type.value,
        "description": clean_desc,
        "severity": payload.severity.value,
        "latitude": float(payload.latitude),
        "longitude": float(payload.longitude),
        "location_accuracy": float(payload.location_accuracy) if payload.location_accuracy is not None else None,
        "location_name": clean_location,
        "district": clean_district,
        "state_region": inferred_region,
        "water_depth": float(water_depth) if water_depth is not None else None,
        "road_status": road_status.value if road_status else None,
        "road_name": clean_road_name,
        "hazard_cause": clean_hazard_cause,
        "reporter_name": clean_reporter_name,
        "reporter_contact": clean_reporter_contact,
        "reported_at": reported_at,
    }
