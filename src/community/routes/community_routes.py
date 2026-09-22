"""
PRAVAH — Community Reporting REST API Router
Exposes endpoints under prefix /api/community for report submission,
moderation, photo uploads, spatial telemetry, and ground-truth intelligence.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from src.community.community_manager import CommunityManager
from src.community.models.incident import (
    CommunityReportCreate,
    CommunityReportResponse,
    CommunityStatsResponse,
    IncidentClusterResponse,
    ReportStatus,
    ReportType,
    RoadStatus,
    SeverityLevel,
    StatusUpdatePayload,
)
from src.community.services.intelligence_pipeline import compute_community_ground_signals

logger = logging.getLogger("pravah.community.routes")

router = APIRouter(prefix="/api/community", tags=["Community Reporting"])


# =============================================================================
# 1. Report Submission Endpoints (JSON & Multipart)
# =============================================================================

@router.post(
    "/reports",
    response_model=CommunityReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Crowdsourced Flood Report (JSON)",
    description="Submit a new citizen flood observation, blocked road, or water-level measurement.",
)
async def submit_report_json(payload: CommunityReportCreate) -> Dict[str, Any]:
    """Accepts JSON payload to register a new community report."""
    return await CommunityManager.submit_report(payload=payload, photo_file=None)


@router.post(
    "/reports/multipart",
    response_model=CommunityReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Report with Photo Attachment (Multipart)",
    description="Submit a new report with an optional image attachment in a single request.",
)
async def submit_report_multipart(
    report_type: ReportType = Form(..., description="Report category"),
    description: str = Form(..., min_length=3, max_length=2000, description="Description of hazard"),
    severity: SeverityLevel = Form(SeverityLevel.MODERATE, description="Severity level"),
    latitude: float = Form(..., ge=-90.0, le=90.0, description="GPS latitude"),
    longitude: float = Form(..., ge=-180.0, le=180.0, description="GPS longitude"),
    location_accuracy: Optional[float] = Form(None, description="GPS accuracy radius in meters"),
    location_name: Optional[str] = Form(None, description="Village / Town / Landmark"),
    district: Optional[str] = Form(None, description="District"),
    state_region: Optional[str] = Form(None, description="State / Region"),
    water_depth: Optional[float] = Form(None, description="Water depth in meters"),
    road_status: Optional[RoadStatus] = Form(None, description="Road passability status"),
    road_name: Optional[str] = Form(None, description="Road or highway name"),
    hazard_cause: Optional[str] = Form(None, description="Hazard cause"),
    reporter_name: Optional[str] = Form(None, description="Reporter name"),
    reporter_contact: Optional[str] = Form(None, description="Reporter contact"),
    timestamp: Optional[str] = Form(None, description="ISO timestamp"),
    photo: Optional[UploadFile] = File(None, description="Incident photo (JPEG/PNG/WebP, max 10MB)"),
) -> Dict[str, Any]:
    """Accepts multipart/form-data with optional photo file."""
    payload = CommunityReportCreate(
        report_type=report_type,
        description=description,
        severity=severity,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=location_accuracy,
        location_name=location_name,
        district=district,
        state_region=state_region,
        water_depth=water_depth,
        road_status=road_status,
        road_name=road_name,
        hazard_cause=hazard_cause,
        reporter_name=reporter_name,
        reporter_contact=reporter_contact,
        timestamp=timestamp,
    )
    return await CommunityManager.submit_report(payload=payload, photo_file=photo)


# =============================================================================
# 2. Report Retrieval & Filtering Endpoints
# =============================================================================

@router.get(
    "/reports",
    response_model=List[CommunityReportResponse],
    summary="List Community Reports",
    description="Retrieve filtered list of community reports for the dashboard and moderation queue.",
)
def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report category"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MODERATE, HIGH, CRITICAL)"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING_REVIEW, VERIFIED, REJECTED, RESOLVED)"),
    region: Optional[str] = Query(None, description="Filter by region (Maharashtra, Northeast)"),
    search: Optional[str] = Query(None, description="Free text search on description, location, or road"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> List[Dict[str, Any]]:
    """Returns filtered community reports."""
    return CommunityManager.list_reports(
        report_type=report_type,
        severity=severity,
        verification_status=status,
        state_region=region,
        search=search,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# 2. Map & Spatial Telemetry (Must precede /reports/{report_id} path parameter)
# =============================================================================

@router.get(
    "/reports/map",
    summary="Get Map GeoJSON FeatureCollection",
    description="Returns standard GeoJSON FeatureCollection of community reports for Leaflet GIS maps.",
)
@router.get(
    "/map",
    summary="Get Map GeoJSON FeatureCollection (Alias)",
    description="Alias endpoint returning standard GeoJSON FeatureCollection.",
)
def get_map_geojson() -> Dict[str, Any]:
    """Returns GeoJSON formatted collection for GIS rendering."""
    return CommunityManager.get_map_data()


# =============================================================================
# 3. Aggregate Statistics & KPI Counters
# =============================================================================

@router.get(
    "/stats",
    response_model=CommunityStatsResponse,
    summary="Community Reports Statistics",
    description="Aggregate counters for the Community Dashboard KPI summary cards.",
)
def get_stats() -> Dict[str, Any]:
    """Returns total, today, pending, verified, and blocked road metrics."""
    return CommunityManager.get_stats()


# =============================================================================
# 4. Incident Clusters
# =============================================================================

@router.get(
    "/clusters",
    response_model=List[IncidentClusterResponse],
    summary="Get Incident Clusters",
    description="Returns grouped spatial-temporal clusters with their child citizen reports.",
)
def get_clusters() -> List[Dict[str, Any]]:
    """Returns grouped incident clusters."""
    return CommunityManager.get_clusters()


# =============================================================================
# 5. Report Detail by ID or Code
# =============================================================================

@router.get(
    "/reports/{report_id}",
    response_model=CommunityReportResponse,
    summary="Get Report by ID or Code",
    description="Retrieve detailed report metadata by numeric ID (e.g. 1) or code (e.g. 'CR-1001').",
)
def get_report(report_id: str) -> Dict[str, Any]:
    """Retrieve single report with full cluster context."""
    return CommunityManager.get_report(report_id)


# =============================================================================
# 6. Moderation Lifecycle Status Transition
# =============================================================================

@router.patch(
    "/reports/{report_id}/status",
    response_model=CommunityReportResponse,
    summary="Update Report Status (Moderation)",
    description="Transition report lifecycle (PENDING_REVIEW, VERIFIED, REJECTED, RESOLVED).",
)
def update_report_status(report_id: int, payload: StatusUpdatePayload) -> Dict[str, Any]:
    """Moderator action to verify, reject, or resolve a community report."""
    return CommunityManager.update_status(report_id=report_id, payload=payload)


# =============================================================================
# 7. Photo Attachment Endpoint
# =============================================================================

@router.post(
    "/reports/{report_id}/photos",
    response_model=CommunityReportResponse,
    summary="Upload Photo to Existing Report",
    description="Attach an additional photographic evidence image to an existing report.",
)
async def upload_report_photo(
    report_id: int,
    photo: UploadFile = File(..., description="Image file (JPEG/PNG/WebP, max 10MB)"),
) -> Dict[str, Any]:
    """Uploads and associates an additional photo with the report."""
    return await CommunityManager.add_photo(report_id=report_id, photo_file=photo)


# =============================================================================
# 8. Ground-Truth Intelligence Pipeline Signals
# =============================================================================

@router.get(
    "/signals",
    summary="Ground-Truth Intelligence Signals",
    description="Computes verified ground-truth signals and confidence scores for PRAVAH predictive pipelines.",
)
def get_ground_signals(
    latitude: Optional[float] = Query(None, description="Optional target latitude to filter around"),
    longitude: Optional[float] = Query(None, description="Optional target longitude to filter around"),
    radius_km: float = Query(25.0, ge=1.0, le=200.0, description="Search radius in km"),
    window_hours: float = Query(6.0, ge=0.5, le=48.0, description="Time window in hours"),
) -> Dict[str, Any]:
    """Computes verified community ground-truth confirmation signals."""
    verified_reports = CommunityManager.list_reports(status="VERIFIED", limit=500)
    return compute_community_ground_signals(
        verified_reports=verified_reports,
        target_lat=latitude,
        target_lon=longitude,
        radius_km=radius_km,
        window_hours=window_hours,
    )
