"""
PRAVAH — SMS Notification Channel Provider
Dispatches concise emergency cellular SMS warnings via SMS gateway API or Twilio SMS,
with automatic presentation sandbox simulation fallback.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
import httpx

from src.alerts.channels.base import BaseAlertChannel
from src.alerts.models.alert import ChannelDeliveryDetail, DeliveryStatus
from src.alerts.utils.helpers import get_current_utc_iso, mask_recipient, normalize_phone_number

logger = logging.getLogger("pravah.alerts.sms")


class SMSAlertChannel(BaseAlertChannel):
    """SMS channel implementation supporting REST gateways & Twilio SMS with sandbox fallback."""

    def __init__(self):
        super().__init__(name="sms")
        self.api_key = os.getenv("SMS_PROVIDER_API_KEY", "").strip()
        self.sender_id = os.getenv("SMS_PROVIDER_SENDER_ID", "PRAVAH").strip()
        self.api_url = os.getenv("SMS_PROVIDER_URL", "").strip()
        # Fallback to Twilio credentials if configured
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_from = os.getenv("TWILIO_SMS_FROM", "+17372212163").strip()
        self.enabled = os.getenv("SMS_ENABLED", "true").lower() in ("true", "1", "yes")

    def is_enabled(self) -> bool:
        return self.enabled

    def get_mode(self) -> str:
        if self.api_key and self.api_url:
            return "LIVE (SMS Gateway)"
        if self.twilio_sid and self.twilio_token and not self.twilio_sid.startswith("YOUR_") and "twilio" not in self.twilio_sid.lower():
            return "LIVE (Twilio SMS)"
        return "SIMULATION (Sandbox)"

    async def send(
        self,
        recipient: str,
        message: str,
        alert_metadata: Optional[Dict[str, Any]] = None,
    ) -> ChannelDeliveryDetail:
        now = get_current_utc_iso()
        norm_phone = normalize_phone_number(recipient)
        masked = mask_recipient(norm_phone)

        # 1. Check if channel is enabled
        if not self.is_enabled():
            return ChannelDeliveryDetail(
                channel="sms",
                recipient=masked,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message="SMS channel is disabled via configuration.",
                timestamp=now,
            )

        # 2. Check for simulation mode
        mode = self.get_mode()
        if "SIMULATION" in mode:
            sim_id = f"SMS_SIM_{abs(hash(norm_phone + message)) % 10000000:07d}"
            logger.info("📱 [SMS SIMULATION] Dispatched to %s: '%s' (ID: %s)", masked, message[:60], sim_id)
            return ChannelDeliveryDetail(
                channel="sms",
                recipient=masked,
                delivery_status=DeliveryStatus.DELIVERED.value,
                message_id=sim_id,
                provider_response=f"Simulated SMS gateway dispatch: message queued for cellular delivery to {masked}.",
                timestamp=now,
            )

        # 3. Live Dispatch via Twilio or HTTP Gateway
        try:
            if self.twilio_sid and self.twilio_token:
                # Live Twilio SMS dispatch
                from twilio.rest import Client
                client = Client(self.twilio_sid, self.twilio_token)
                msg_record = client.messages.create(
                    to=norm_phone,
                    from_=self.twilio_from,
                    body=message,
                )
                logger.info("📱 [SMS LIVE] Dispatched via Twilio to %s (SID: %s)", masked, msg_record.sid)
                return ChannelDeliveryDetail(
                    channel="sms",
                    recipient=masked,
                    delivery_status=DeliveryStatus.SENT.value,
                    message_id=msg_record.sid,
                    provider_response=f"Twilio SMS accepted: status '{msg_record.status}'.",
                    timestamp=now,
                )
            elif self.api_url and self.api_key:
                # Generic HTTP SMS Gateway
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        self.api_url,
                        json={"to": norm_phone, "sender": self.sender_id, "text": message},
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                    if resp.is_success:
                        return ChannelDeliveryDetail(
                            channel="sms",
                            recipient=masked,
                            delivery_status=DeliveryStatus.SENT.value,
                            message_id=f"SMS_{resp.status_code}",
                            provider_response=resp.text[:200],
                            timestamp=now,
                        )
                    else:
                        return ChannelDeliveryDetail(
                            channel="sms",
                            recipient=masked,
                            delivery_status=DeliveryStatus.FAILED.value,
                            error_message=f"SMS Gateway HTTP error: {resp.status_code}",
                            timestamp=now,
                        )
        except Exception as exc:
            logger.error("SMS dispatch failure to %s: %s", masked, exc)
            return ChannelDeliveryDetail(
                channel="sms",
                recipient=masked,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message=str(exc),
                timestamp=now,
            )

        return ChannelDeliveryDetail(
            channel="sms",
            recipient=masked,
            delivery_status=DeliveryStatus.FAILED.value,
            error_message="SMS provider configuration unavailable.",
            timestamp=now,
        )
