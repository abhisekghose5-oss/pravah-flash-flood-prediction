"""
PRAVAH — Multi-Channel Alert Data Models & Pydantic Schemas
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EVACUATION = "EVACUATION"


class TriggerType(str, Enum):
    RISK_SCORE = "RISK_SCORE"
    RIVER_LEVEL = "RIVER_LEVEL"
    RAINFALL_FORECAST = "RAINFALL_FORECAST"
    MANUAL_DISPATCH = "MANUAL_DISPATCH"
    MULTI_FACTOR = "MULTI_FACTOR"


class ChannelType(str, Enum):
    SMS = "sms"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    IVRS = "ivrs"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class AlertTriggerRequest(BaseModel):
    """Payload to evaluate conditions and trigger multi-channel alert dispatch."""
    location: str = Field(..., description="Catchment or municipal zone name", examples=["Karad"])
    region: Optional[str] = Field("Maharashtra", description="State or operational region", examples=["Maharashtra"])
    risk_score: Optional[float] = Field(None, description="Risk probability percentage (e.g. 78.5 or 0.785)", examples=[78.5])
    river_level: Optional[float] = Field(None, description="Current monitored river stage in meters", examples=[8.7])
    river_threshold: Optional[float] = Field(None, description="River warning threshold in meters", examples=[8.0])
    rainfall_forecast: Optional[float] = Field(None, description="Forecast rainfall in millimeters", examples=[180.0])
    alert_type: Optional[TriggerType] = Field(None, description="Optional override trigger type", examples=["RISK_SCORE"])
    severity: Optional[AlertSeverity] = Field(None, description="Optional explicit severity override")
    channels: Optional[List[ChannelType]] = Field(None, description="Specific channels to dispatch to; defaults to all enabled")
    custom_recipient_phone: Optional[str] = Field(None, description="Custom phone number for SMS/WhatsApp testing", examples=["+919876543210"])
    custom_telegram_chat_id: Optional[str] = Field(None, description="Custom Telegram chat ID", examples=["@pravah_alerts"])
    evacuation_route: Optional[str] = Field(None, description="Designated evacuation route", examples=["SH-72 towards North Ridge"])
    shelter_location: Optional[str] = Field(None, description="Designated relief shelter", examples=["Karad Municipal High Ground Staging Hall"])
    message_override: Optional[str] = Field(None, description="Optional custom broadcast text")


class ChannelDeliveryDetail(BaseModel):
    """Delivery status breakdown per communication channel."""
    channel: str
    recipient: str
    delivery_status: str
    message_id: Optional[str] = None
    provider_response: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str


class AlertRecordResponse(BaseModel):
    """Complete record of an alert broadcast and its delivery channels."""
    id: int
    alert_code: str
    timestamp: str
    location: str
    region: Optional[str] = None
    alert_type: str
    severity: str
    trigger_reason: str
    risk_score: Optional[float] = None
    river_level: Optional[float] = None
    river_threshold: Optional[float] = None
    rainfall_forecast: Optional[float] = None
    evacuation_route: Optional[str] = None
    shelter_location: Optional[str] = None
    overall_status: str
    channels: List[ChannelDeliveryDetail] = Field(default_factory=list)
    created_at: str


class AlertStatsResponse(BaseModel):
    """Aggregate statistics for the Alerts Center dashboard."""
    total_alerts: int
    critical_alerts: int
    warnings: int
    evacuation_alerts: int
    successful_deliveries: int
    failed_deliveries: int
    timestamp: str


class ChannelStatusResponse(BaseModel):
    """Operational status of communication channels."""
    sms_enabled: bool
    sms_mode: str
    whatsapp_enabled: bool
    whatsapp_mode: str
    telegram_enabled: bool
    telegram_mode: str
    ivrs_enabled: bool = True
    ivrs_mode: str = "SIMULATION (Sandbox)"
    timestamp: str
    sms: Optional[Dict[str, Any]] = None
    whatsapp: Optional[Dict[str, Any]] = None
    telegram: Optional[Dict[str, Any]] = None
    ivrs: Optional[Dict[str, Any]] = None
