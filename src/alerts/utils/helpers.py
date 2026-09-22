"""
PRAVAH — Alert Utilities & Helpers
Provides phone number formatting, PII masking, alert ID generation, and timestamp utilities.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional


def normalize_phone_number(phone: Optional[str], default_country_code: str = "+91") -> str:
    """
    Normalizes a mobile phone number to standard E.164 format.
    Example: '9876543210' -> '+919876543210', '09876543210' -> '+919876543210'
    """
    if not phone:
        return ""
    cleaned = re.sub(r"[^\d+]", "", str(phone).strip())
    if not cleaned:
        return ""
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("0"):
        cleaned = cleaned[1:]
    if len(cleaned) == 10 and not cleaned.startswith("91"):
        return f"{default_country_code}{cleaned}"
    if len(cleaned) == 12 and cleaned.startswith("91"):
        return f"+{cleaned}"
    return f"+{cleaned}"


def mask_recipient(recipient: Optional[str]) -> str:
    """
    Mask recipient phone number or Telegram chat ID for privacy protection.
    Example: '+919876543210' -> '+91 ******3210'
    """
    if not recipient:
        return "Unknown Recipient"
    s = str(recipient).strip()
    if s.startswith("whatsapp:"):
        s = s.replace("whatsapp:", "")
    if s.startswith("+") and len(s) >= 8:
        prefix = s[:3]
        suffix = s[-4:]
        return f"{prefix} ******{suffix}"
    if len(s) > 6:
        return f"{s[:2]}***{s[-2:]}"
    return "***"


def generate_alert_code(row_id: int) -> str:
    """Generates standardized PRAVAH alert code (e.g. 'ALT-1042')."""
    return f"ALT-{1000 + row_id}"


def get_current_utc_iso() -> str:
    """Return standard ISO 8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()
