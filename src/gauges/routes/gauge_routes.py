"""
PRAVAH — River Gauge Monitoring REST API Router.
Mounted under /api/gauges to provide real-time hydrometric observation,
warning/danger threshold monitoring, and historical river-level trends.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from src.gauges.models.gauge import (
    RiverGauge,
    RiverGaugeHistoryPoint,
    RiverGaugeObservationRequest,
    RiverGaugeStatus,
    ThresholdEvaluationResult,
)
from src.gauges.gauge_service import get_gauge_service

router = APIRouter(prefix="/api/gauges", tags=["River Gauge Monitoring"])


@router.get("", response_model=List[RiverGauge], summary="List All Monitored River Gauges")
def list_river_gauges(
    region: Optional[str] = Query(None, description="Filter: 'Maharashtra' or 'Northeast'"),
    status_filter: Optional[RiverGaugeStatus] = Query(None, alias="status", description="Filter: 'NORMAL', 'WARNING', 'DANGER'"),
) -> List[RiverGauge]:
    """
    Retrieve real-time catalog of monitored CWC and Northeast river gauges,
    including current water level, warning/danger marks, and 24-hour rate-of-rise trends.
    """
    service = get_gauge_service()
    return service.list_gauges(region=region, status=status_filter)


@router.get("/{gauge_id}", response_model=RiverGauge, summary="Get River Gauge Telemetry by ID")
def get_gauge_detail(gauge_id: str) -> RiverGauge:
    """
    Retrieve live telemetry, coordinate locations, and threshold marks for a specific gauge.
    Accepts raw IDs (e.g. '684'), prefixed IDs ('INDOFLOODS-gauge-684'), or Northeast IDs ('NE-Beki').
    """
    service = get_gauge_service()
    g = service.get_gauge(gauge_id)
    if not g:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"River gauge '{gauge_id}' not found in registry",
        )
    return g


@router.get("/{gauge_id}/history", response_model=List[RiverGaugeHistoryPoint], summary="Get River Stage Time Series")
def get_gauge_history(
    gauge_id: str,
    limit: int = Query(24, ge=1, le=168, description="Number of historical hours/steps to retrieve"),
) -> List[RiverGaugeHistoryPoint]:
    """
    Retrieve chronological river-stage hydrograph observations for trend charting.
    """
    service = get_gauge_service()
    g = service.get_gauge(gauge_id)
    if not g:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"River gauge '{gauge_id}' not found",
        )
    return service.get_history(gauge_id, limit=limit)


@router.post("/{gauge_id}/observe", response_model=ThresholdEvaluationResult, summary="Record River Level Observation")
def record_gauge_observation(
    gauge_id: str,
    request: RiverGaugeObservationRequest,
) -> ThresholdEvaluationResult:
    """
    Submit a live or manual hydrometric water-level reading for a gauge station.
    Updates the live telemetry, logs the observation to database, and evaluates warning/danger thresholds.
    """
    service = get_gauge_service()
    g = service.get_gauge(gauge_id)
    if not g:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"River gauge '{gauge_id}' not found",
        )
    return service.record_observation(
        gauge_id=gauge_id,
        water_level_m=request.water_level_m,
        source=request.source or "MANUAL_TELEMETRY",
        timestamp_utc=request.timestamp_utc,
    )
