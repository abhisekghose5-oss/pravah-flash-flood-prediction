"""
PRAVAH — Base Alert Channel Interface
Defines the abstract notification channel protocol for SMS, WhatsApp, and Telegram.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from src.alerts.models.alert import ChannelDeliveryDetail


class BaseAlertChannel(ABC):
    """Abstract interface that all notification channel providers must implement."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def is_enabled(self) -> bool:
        """Returns True if the channel provider is configured and active."""
        pass

    @abstractmethod
    def get_mode(self) -> str:
        """Returns 'LIVE' if real provider credentials are set, or 'SIMULATION' fallback."""
        pass

    @abstractmethod
    async def send(
        self,
        recipient: str,
        message: str,
        alert_metadata: Optional[Dict[str, Any]] = None,
    ) -> ChannelDeliveryDetail:
        """
        Dispatches the alert message to the designated recipient.
        Must handle exceptions gracefully and return a ChannelDeliveryDetail.
        """
        pass
