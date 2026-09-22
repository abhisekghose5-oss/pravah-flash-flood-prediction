"""
PRAVAH — WhatsApp Notification Channel Provider
Dispatches rich, emoji-badged flood disaster warnings to citizens via
WhatsApp Cloud API or Twilio WhatsApp, with automatic presentation sandbox fallback.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
import httpx

from src.alerts.channels.base import BaseAlertChannel
from src.alerts.models.alert import ChannelDeliveryDetail, DeliveryStatus
from src.alerts.utils.helpers import get_current_utc_iso, mask_recipient, normalize_phone_number

logger = logging.getLogger("pravah.alerts.whatsapp")


class WhatsAppAlertChannel(BaseAlertChannel):
    """WhatsApp notification provider with provider-agnostic dispatch and simulation fallback."""

    def __init__(self):
        super().__init__(name="whatsapp")
        self.api_key = os.getenv("WHATSAPP_API_KEY", "").strip()
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
        self.api_url = os.getenv("WHATSAPP_API_URL", "").strip()
        # Fallback to Twilio WhatsApp
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_from = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+17372212163").strip()
        self.enabled = os.getenv("WHATSAPP_ENABLED", "true").lower() in ("true", "1", "yes")

    def is_enabled(self) -> bool:
        return self.enabled

    def get_mode(self) -> str:
        if self.api_key and self.phone_number_id:
            return "LIVE (Meta WhatsApp Cloud API)"
        if self.twilio_sid and self.twilio_token and not self.twilio_sid.startswith("YOUR_") and "twilio" not in self.twilio_sid.lower():
            return "LIVE (Twilio WhatsApp)"
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
                channel="whatsapp",
                recipient=masked,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message="WhatsApp channel is disabled via configuration.",
                timestamp=now,
            )

        # 2. Check for simulation mode
        mode = self.get_mode()
        if "SIMULATION" in mode:
            sim_id = f"WA_SIM_{abs(hash(norm_phone + message)) % 10000000:07d}"
            logger.info("💬 [WHATSAPP SIMULATION] Dispatched to %s: '%s' (ID: %s)", masked, message[:60], sim_id)
            return ChannelDeliveryDetail(
                channel="whatsapp",
                recipient=masked,
                delivery_status=DeliveryStatus.DELIVERED.value,
                message_id=sim_id,
                provider_response=f"Simulated WhatsApp message delivered to {masked}.",
                timestamp=now,
            )

        # 3. Live Dispatch
        try:
            # Twilio WhatsApp flow
            if self.twilio_sid and self.twilio_token:
                from twilio.rest import Client
                to_wa = f"whatsapp:{norm_phone}" if not norm_phone.startswith("whatsapp:") else norm_phone
                from_wa = self.twilio_from if self.twilio_from.startswith("whatsapp:") else f"whatsapp:{self.twilio_from}"
                client = Client(self.twilio_sid, self.twilio_token)
                msg_record = client.messages.create(
                    to=to_wa,
                    from_=from_wa,
                    body=message,
                )
                logger.info("💬 [WHATSAPP LIVE] Dispatched to %s (SID: %s)", masked, msg_record.sid)
                return ChannelDeliveryDetail(
                    channel="whatsapp",
                    recipient=masked,
                    delivery_status=DeliveryStatus.SENT.value,
                    message_id=msg_record.sid,
                    provider_response=f"Twilio WhatsApp queued: status '{msg_record.status}'.",
                    timestamp=now,
                )
            # Meta WhatsApp Cloud API flow
            elif self.api_key and self.phone_number_id:
                clean_digits = norm_phone.replace("+", "")
                url = self.api_url or f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        json={
                            "messaging_product": "whatsapp",
                            "to": clean_digits,
                            "type": "text",
                            "text": {"body": message},
                        },
                    )
                    if resp.is_success:
                        return ChannelDeliveryDetail(
                            channel="whatsapp",
                            recipient=masked,
                            delivery_status=DeliveryStatus.SENT.value,
                            message_id=resp.json().get("messages", [{}])[0].get("id", "WA_LIVE"),
                            provider_response="Meta WhatsApp Cloud API accepted.",
                            timestamp=now,
                        )
                    else:
                        return ChannelDeliveryDetail(
                            channel="whatsapp",
                            recipient=masked,
                            delivery_status=DeliveryStatus.FAILED.value,
                            error_message=f"WhatsApp Cloud API error {resp.status_code}: {resp.text[:200]}",
                            timestamp=now,
                        )
        except Exception as exc:
            logger.error("WhatsApp dispatch failure to %s: %s", masked, exc)
            return ChannelDeliveryDetail(
                channel="whatsapp",
                recipient=masked,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message=str(exc),
                timestamp=now,
            )

        return ChannelDeliveryDetail(
            channel="whatsapp",
            recipient=masked,
            delivery_status=DeliveryStatus.FAILED.value,
            error_message="WhatsApp provider credentials unconfigured.",
            timestamp=now,
        )
