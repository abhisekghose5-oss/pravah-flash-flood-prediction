"""
PRAVAH — Multi-Channel Alert REST API Router
Exposes endpoints under prefix /api/alerts for trigger evaluation,
channel delivery status tracking, statistics, and alert history.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from src.alerts.alert_manager import alert_manager
from src.alerts.models.alert import (
    AlertRecordResponse,
    AlertStatsResponse,
    AlertTriggerRequest,
    ChannelStatusResponse,
)

logger = logging.getLogger("pravah.alerts.routes")

router = APIRouter(prefix="/api/alerts", tags=["Multi-Channel Alerts"])


# =============================================================================
# 1. Trigger Multi-Channel Alert (Automated or Manual)
# =============================================================================

@router.post(
    "/trigger",
    status_code=status.HTTP_200_OK,
    summary="Trigger Multi-Channel Flood Alert",
    description="Evaluates hydrological hazard criteria and dispatches concurrent SMS, WhatsApp, and Telegram warnings.",
)
async def trigger_multichannel_alert(payload: AlertTriggerRequest) -> Dict[str, Any]:
    """Evaluates telemetry triggers and initiates multi-channel broadcast."""
    return await alert_manager.trigger_alert(payload)


# =============================================================================
# 2. Alert Statistics & KPI Counters (Must precede /{alert_id} dynamic parameter)
# =============================================================================

@router.get(
    "/stats",
    response_model=AlertStatsResponse,
    summary="Get Alert Statistics",
    description="Returns aggregate KPI counters for the Alerts Center dashboard.",
)
def get_alert_stats() -> Dict[str, Any]:
    """Returns total, critical, warnings, evacuations, and delivery counts."""
    return alert_manager.get_stats()


# =============================================================================
# 3. Channel Health & Operational Mode Status
# =============================================================================

@router.get(
    "/status",
    response_model=ChannelStatusResponse,
    summary="Get Channel Providers Status",
    description="Returns connectivity and operating mode (LIVE vs SIMULATION) for SMS, WhatsApp, and Telegram.",
)
def get_channel_status() -> Dict[str, Any]:
    """Returns provider status for each notification channel."""
    return alert_manager.get_channel_statuses().model_dump()


# =============================================================================
# 4. Alert History Endpoints
# =============================================================================

@router.get(
    "",
    response_model=List[AlertRecordResponse],
    summary="List Alert History",
    description="Retrieves chronological flood alert records with per-channel delivery details.",
)
@router.get(
    "/history",
    response_model=List[AlertRecordResponse],
    summary="List Alert History (Alias)",
    description="Alias endpoint returning historical alerts.",
)
def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity (WARNING, CRITICAL, EVACUATION)"),
    channel: Optional[str] = Query(None, description="Filter by channel (sms, whatsapp, telegram)"),
    location: Optional[str] = Query(None, description="Filter by location/catchment name"),
    status: Optional[str] = Query(None, description="Filter by overall status (DELIVERED, PARTIAL, FAILED)"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> List[Dict[str, Any]]:
    """Returns filtered alert history."""
    return alert_manager.list_alerts(
        severity=severity,
        channel=channel,
        location=location,
        status=status,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# 5. Single Alert Record Detail by ID or Code
# =============================================================================

@router.get(
    "/{alert_id}",
    response_model=AlertRecordResponse,
    summary="Get Alert Details by ID or Code",
    description="Retrieves a single alert record and the delivery breakdown across SMS, WhatsApp, and Telegram.",
)
def get_alert_detail(alert_id: str) -> Dict[str, Any]:
    """Fetch single alert record."""
    alert = alert_manager.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found."
        )
    return alert
