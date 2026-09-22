"""
PRAVAH — Telegram Bot Notification Channel Provider
Dispatches flood warnings to emergency response channels, groups, and citizen subscribers
via the Telegram Bot API, with automatic presentation sandbox fallback.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
import httpx

from src.alerts.channels.base import BaseAlertChannel
from src.alerts.models.alert import ChannelDeliveryDetail, DeliveryStatus
from src.alerts.utils.helpers import get_current_utc_iso, mask_recipient

logger = logging.getLogger("pravah.alerts.telegram")


class TelegramAlertChannel(BaseAlertChannel):
    """Telegram Bot notification channel implementation with sandbox simulation fallback."""

    def __init__(self):
        super().__init__(name="telegram")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.default_chat_id = os.getenv("TELEGRAM_CHAT_ID", "@pravah_flood_alerts").strip()
        self.api_url = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org").strip()
        self.enabled = os.getenv("TELEGRAM_ENABLED", "true").lower() in ("true", "1", "yes")

    def is_enabled(self) -> bool:
        return self.enabled

    def get_mode(self) -> str:
        if self.bot_token and not self.bot_token.startswith("YOUR_") and "bot" not in self.bot_token.lower():
            return "LIVE (Telegram Bot API)"
        return "SIMULATION (Sandbox)"

    async def send(
        self,
        recipient: str,
        message: str,
        alert_metadata: Optional[Dict[str, Any]] = None,
    ) -> ChannelDeliveryDetail:
        now = get_current_utc_iso()
        target_chat = recipient or self.default_chat_id
        masked = mask_recipient(target_chat)

        # 1. Check if channel is enabled
        if not self.is_enabled():
            return ChannelDeliveryDetail(
                channel="telegram",
                recipient=masked,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message="Telegram channel is disabled via configuration.",
                timestamp=now,
            )

        # 2. Check for simulation mode
        mode = self.get_mode()
        if "SIMULATION" in mode:
            sim_id = f"TG_SIM_{abs(hash(target_chat + message)) % 10000000:07d}"
            logger.info("✈ [TELEGRAM SIMULATION] Dispatched to %s: '%s' (ID: %s)", masked, message[:60], sim_id)
            return ChannelDeliveryDetail(
                channel="telegram",
                recipient=masked,
                delivery_status=DeliveryStatus.DELIVERED.value,
                message_id=sim_id,
                provider_response=f"Simulated Telegram broadcast to chat {masked}.",
                timestamp=now,
            )

        # 3. Live Dispatch via Telegram Bot API
        try:
            endpoint = f"{self.api_url}/bot{self.bot_token}/sendMessage"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    endpoint,
                    json={
                        "chat_id": target_chat,
                        "text": message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
                if resp.is_success:
                    data = resp.json()
                    msg_id = str(data.get("result", {}).get("message_id", "TG_SENT"))
                    logger.info("✈ [TELEGRAM LIVE] Broadcast succeeded to %s (Msg ID: %s)", masked, msg_id)
                    return ChannelDeliveryDetail(
                        channel="telegram",
                        recipient=masked,
                        delivery_status=DeliveryStatus.SENT.value,
                        message_id=msg_id,
                        provider_response="Telegram Bot API confirmed delivery.",
                        timestamp=now,
                    )
                else:
                    logger.error("Telegram API HTTP error %d: %s", resp.status_code, resp.text)
                    return ChannelDeliveryDetail(
                        channel="telegram",
                        recipient=masked,
                        delivery_status=DeliveryStatus.FAILED.value,
                        error_message=f"Telegram API HTTP error: {resp.status_code}",
                        timestamp=now,
                    )
        except Exception as exc:
            logger.error("Telegram dispatch failure to %s: %s", masked, exc)
            return ChannelDeliveryDetail(
                channel="telegram",
                recipient=masked,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message=str(exc),
                timestamp=now,
            )
