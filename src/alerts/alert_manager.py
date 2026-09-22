"""
PRAVAH — Central Alert Manager Orchestration Layer
Coordinates rule evaluation, template rendering, fault-tolerant concurrent
multi-channel dispatch (SMS, WhatsApp, Telegram), cooldown protection, and history tracking.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.alerts.alert_rules import AlertEvaluationResult, evaluate_alert_rules
from src.alerts.alert_service import (
    get_alert_by_id,
    get_alert_statistics,
    get_alerts_history,
    get_last_alert_time,
    save_alert_record,
    save_channel_delivery,
)
from src.alerts.alert_templates import render_alert_message
from src.alerts.channels.sms import SMSAlertChannel
from src.alerts.channels.telegram import TelegramAlertChannel
from src.alerts.channels.whatsapp import WhatsAppAlertChannel
from src.alerts.channels.ivrs import IVRSAlertChannel
from src.alerts.models.alert import (
    AlertRecordResponse,
    AlertSeverity,
    AlertTriggerRequest,
    ChannelDeliveryDetail,
    ChannelStatusResponse,
    ChannelType,
    DeliveryStatus,
    TriggerType,
)
from src.alerts.utils.helpers import get_current_utc_iso

logger = logging.getLogger("pravah.alerts.manager")

# Configurable alert cooldown in minutes
ALERT_COOLDOWN_MINUTES: int = int(os.getenv("ALERT_COOLDOWN_MINUTES", "15"))


class AlertManager:
    """Central orchestration service for PRAVAH multi-channel disaster alerts."""

    def __init__(self):
        # Register notification channels
        self.sms_channel = SMSAlertChannel()
        self.whatsapp_channel = WhatsAppAlertChannel()
        self.telegram_channel = TelegramAlertChannel()
        self.ivrs_channel = IVRSAlertChannel()

    def get_channel_statuses(self) -> ChannelStatusResponse:
        """Returns the active operating status of each notification provider."""
        sms_mode = self.sms_channel.get_mode()
        wa_mode = self.whatsapp_channel.get_mode()
        tg_mode = self.telegram_channel.get_mode()
        ivrs_mode = self.ivrs_channel.get_mode()
        return ChannelStatusResponse(
            sms_enabled=self.sms_channel.is_enabled(),
            sms_mode=sms_mode,
            whatsapp_enabled=self.whatsapp_channel.is_enabled(),
            whatsapp_mode=wa_mode,
            telegram_enabled=self.telegram_channel.is_enabled(),
            telegram_mode=tg_mode,
            ivrs_enabled=self.ivrs_channel.is_enabled(),
            ivrs_mode=ivrs_mode,
            timestamp=get_current_utc_iso(),
            sms={
                "enabled": self.sms_channel.is_enabled(),
                "is_simulated": "SIMULATION" in sms_mode,
                "provider": "Twilio SMS",
            },
            whatsapp={
                "enabled": self.whatsapp_channel.is_enabled(),
                "is_simulated": "SIMULATION" in wa_mode,
                "provider": "WhatsApp Cloud API",
            },
            telegram={
                "enabled": self.telegram_channel.is_enabled(),
                "is_simulated": "SIMULATION" in tg_mode,
                "provider": "@PravahFloodAlertsBot",
            },
            ivrs={
                "enabled": self.ivrs_channel.is_enabled(),
                "is_simulated": "SIMULATION" in ivrs_mode,
                "provider": "Twilio Voice API",
            },
        )

    def is_in_cooldown(self, location: str, severity: AlertSeverity) -> bool:
        """
        Check if an identical alert was sent recently within ALERT_COOLDOWN_MINUTES.
        Severity escalation (e.g. WARNING -> CRITICAL or CRITICAL -> EVACUATION)
        is NEVER blocked by cooldown.
        """
        last_ts = get_last_alert_time(location, severity.value)
        if not last_ts:
            return False

        now = datetime.now(timezone.utc)
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)

        elapsed = now - last_ts
        if elapsed < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
            logger.info(
                "⏳ Alert cooldown active for %s [%s]: %.1f mins remaining.",
                location, severity.value, ALERT_COOLDOWN_MINUTES - (elapsed.total_seconds() / 60.0)
            )
            return True
        return False

    async def trigger_alert(
        self,
        request: AlertTriggerRequest,
    ) -> Dict[str, Any]:
        """
        Evaluates criteria, determines severity, checks duplicate cooldowns,
        and dispatches across enabled channels with failure isolation.
        """
        now = get_current_utc_iso()

        # 1. Evaluate alert rules & determine severity
        eval_result: AlertEvaluationResult = evaluate_alert_rules(
            risk_score=request.risk_score,
            river_level=request.river_level,
            river_threshold=request.river_threshold,
            rainfall_forecast=request.rainfall_forecast,
            explicit_severity=request.severity,
        )

        if not eval_result.is_triggered:
            return {
                "status": "bypassed",
                "message": "Alert conditions not met: telemetry within safe operational bounds.",
                "evaluation": {
                    "is_triggered": False,
                    "reason": eval_result.trigger_reason,
                    "risk_percentage": eval_result.risk_percentage,
                },
                "timestamp": now,
            }

        sev = eval_result.severity
        loc = request.location
        trigger_type = request.alert_type.value if request.alert_type else eval_result.trigger_type.value

        # 2. Duplicate Check (Bypassed if severity escalated or manual override)
        if request.severity is None and self.is_in_cooldown(loc, sev):
            return {
                "status": "cooldown_suppressed",
                "message": f"Alert suppressed by {ALERT_COOLDOWN_MINUTES}m duplicate cooldown for {loc} [{sev.value}].",
                "severity": sev.value,
                "timestamp": now,
            }

        # 3. Context for Message Templates
        template_context = {
            "location": loc,
            "risk_percentage": eval_result.risk_percentage,
            "river_level": request.river_level,
            "river_threshold": request.river_threshold,
            "rainfall_forecast": request.rainfall_forecast,
            "timestamp": now,
            "alert_type": trigger_type,
            "evacuation_route": request.evacuation_route,
            "shelter_location": request.shelter_location,
        }

        # 4. Determine Target Channels
        target_channels = set()
        if request.channels:
            for c in request.channels:
                target_channels.add(c.value.lower())
        else:
            if self.sms_channel.is_enabled():
                target_channels.add("sms")
            if self.whatsapp_channel.is_enabled():
                target_channels.add("whatsapp")
            if self.telegram_channel.is_enabled():
                target_channels.add("telegram")
            if self.ivrs_channel.is_enabled():
                target_channels.add("ivrs")

        # 5. Determine Recipients
        sms_recipient = request.custom_recipient_phone or "+919876543210"
        wa_recipient = request.custom_recipient_phone or "+919876543210"
        tg_recipient = request.custom_telegram_chat_id or self.telegram_channel.default_chat_id
        ivrs_recipient = request.custom_recipient_phone or "+919876543210"

        # 6. Concurrently Dispatch with Strict Error Isolation
        tasks = []
        task_names = []

        if "sms" in target_channels:
            sms_msg = request.message_override or render_alert_message(sev, "sms", template_context)
            tasks.append(self.sms_channel.send(sms_recipient, sms_msg, template_context))
            task_names.append("sms")

        if "whatsapp" in target_channels:
            wa_msg = request.message_override or render_alert_message(sev, "whatsapp", template_context)
            tasks.append(self.whatsapp_channel.send(wa_recipient, wa_msg, template_context))
            task_names.append("whatsapp")

        if "telegram" in target_channels:
            tg_msg = request.message_override or render_alert_message(sev, "telegram", template_context)
            tasks.append(self.telegram_channel.send(tg_recipient, tg_msg, template_context))
            task_names.append("telegram")

        if "ivrs" in target_channels:
            ivrs_msg = request.message_override or render_alert_message(sev, "ivrs", template_context)
            tasks.append(self.ivrs_channel.send(ivrs_recipient, ivrs_msg, template_context))
            task_names.append("ivrs")

        # Gather results concurrently with return_exceptions=True so one failure never stops others
        delivery_results: List[ChannelDeliveryDetail] = []
        if tasks:
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)
            for idx, res in enumerate(raw_results):
                ch_name = task_names[idx]
                if isinstance(res, Exception):
                    logger.error("Channel %s exception: %s", ch_name, res)
                    delivery_results.append(ChannelDeliveryDetail(
                        channel=ch_name,
                        recipient=sms_recipient if ch_name in ("sms", "whatsapp", "ivrs") else tg_recipient,
                        delivery_status=DeliveryStatus.FAILED.value,
                        error_message=str(res),
                        timestamp=now,
                    ))
                elif isinstance(res, ChannelDeliveryDetail):
                    delivery_results.append(res)

        # 7. Compute Overall Alert Status
        success_count = sum(1 for d in delivery_results if d.delivery_status in (DeliveryStatus.SENT.value, DeliveryStatus.DELIVERED.value))
        if success_count == len(delivery_results) and len(delivery_results) > 0:
            overall_status = "DELIVERED"
        elif success_count > 0:
            overall_status = "PARTIAL"
        else:
            overall_status = "FAILED"

        # 8. Persist Alert & Delivery Records to Database
        row_id = save_alert_record(
            location=loc,
            region=request.region,
            alert_type=trigger_type,
            severity=sev.value,
            trigger_reason=eval_result.trigger_reason,
            risk_score=eval_result.risk_percentage,
            river_level=request.river_level,
            river_threshold=request.river_threshold,
            rainfall_forecast=request.rainfall_forecast,
            evacuation_route=request.evacuation_route,
            shelter_location=request.shelter_location,
            overall_status=overall_status,
            timestamp=now,
        )

        for deliv in delivery_results:
            save_channel_delivery(row_id, deliv)

        alert_record = get_alert_by_id(row_id)
        logger.info("🚨 Multi-channel alert #%d [%s] dispatched to %d channels: Status %s",
                    row_id, sev.value, len(delivery_results), overall_status)

        return alert_record or {
            "id": row_id,
            "status": overall_status,
            "severity": sev.value,
            "channels": [d.model_dump() for d in delivery_results],
        }

    # Backward-compatible alias
    dispatch_alert = trigger_alert

    def list_alerts(
        self,
        severity: Optional[str] = None,
        channel: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical alerts."""
        return get_alerts_history(
            severity=severity,
            channel=channel,
            location=location,
            status=status,
            limit=limit,
            offset=offset,
        )

    def get_alert(self, identifier: str | int) -> Optional[Dict[str, Any]]:
        """Retrieve single alert details with channel breakdown."""
        return get_alert_by_id(identifier)

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate statistics for KPI summary cards."""
        return get_alert_statistics()


# Global singleton instance
alert_manager = AlertManager()
