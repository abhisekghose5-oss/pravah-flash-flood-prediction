"""
PRAVAH — IVRS Automated Voice Calling REST API Router.
Mounted under /api/ivrs to provide voice calling dispatch and status tracking.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator

from src.alerts.alert_manager import AlertManager
from src.alerts.channels.ivrs import IVRSAlertChannel

router = APIRouter(prefix="/api/ivrs", tags=["IVRS Voice Calling System"])
_ivrs_channel = IVRSAlertChannel()


class DirectCallRequest(BaseModel):
    """Payload to trigger an emergency outbound voice call."""
    recipient_phone: str = Field(..., description="Target phone number in E.164 format", examples=["+919876543210"])
    message: str = Field(..., description="Spoken message text or emergency script")
    severity: Optional[str] = Field("CRITICAL", description="Alert severity: WARNING, CRITICAL, or EVACUATION")
    alert_code: Optional[str] = Field("IVRS-DIRECT", description="Reference alert code")

    @model_validator(mode='before')
    @classmethod
    def check_phone_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "recipient_phone" not in d or not d["recipient_phone"]:
                phone = d.get("phone") or d.get("recipient") or d.get("to") or d.get("mobile")
                if phone:
                    d["recipient_phone"] = str(phone)
            return d
        return data


@router.post("/call", summary="Dispatch Emergency Outbound Voice Call")
async def trigger_voice_call(request: DirectCallRequest) -> Dict[str, Any]:
    """
    Trigger an immediate automated voice phone call to an emergency contact or resident.
    Utilizes Twilio Voice API when configured or sandbox presentation simulator fallback.
    """
    metadata = {
        "alert_code": request.alert_code,
        "severity": request.severity,
    }
    result = await _ivrs_channel.send(
        recipient=request.recipient_phone,
        message=request.message,
        alert_metadata=metadata,
    )

    return {
        "status": "success" if result.delivery_status in ("SENT", "DELIVERED") else "failed",
        "channel": "ivrs",
        "recipient": result.recipient,
        "delivery_status": result.delivery_status,
        "call_id": result.message_id,
        "provider_call_sid": result.message_id,
        "error_message": result.error_message,
        "mode": _ivrs_channel.get_mode(),
        "timestamp_utc": result.timestamp,
    }


@router.get("/status/{call_id}", summary="Check Outbound Voice Call Status")
async def get_call_status(call_id: str) -> Dict[str, Any]:
    """
    Retrieve real-time delivery status, duration, and metadata for a specific voice call.
    """
    record = _ivrs_channel.get_call_status(call_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call record '{call_id}' not found",
        )
    return record


@router.get("/calls", summary="List Outbound Voice Call History")
async def list_recent_calls(limit: int = Query(20, ge=1, le=100)) -> List[Dict[str, Any]]:
    """
    Retrieve audit history of recent automated voice emergency calls.
    """
    return _ivrs_channel.list_calls(limit=limit)
