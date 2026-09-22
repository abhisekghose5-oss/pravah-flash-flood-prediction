"""
PRAVAH — Community Reporting Utilities & Helpers
Provides text sanitization, anonymization, ID generation, and spatial math.
"""

from __future__ import annotations

import html
import math
import re
from datetime import datetime, timezone
from typing import Optional


def sanitize_text(text: Optional[str], max_length: int = 2000) -> str:
    """
    Sanitize user-provided text to prevent XSS and remove malicious markup.
    Strips dangerous HTML/script tags while preserving natural punctuation.
    Truncates at max_length.
    """
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]*?>", "", str(text))
    # Strip dangerous Javascript pseudo-protocols and script patterns
    clean = re.sub(r"(?i)javascript:", "", clean)
    clean = re.sub(r"(?i)data:\s*text/html", "", clean)
    return clean.strip()[:max_length]


def mask_phone_number(phone: Optional[str]) -> Optional[str]:
    """
    Mask phone number for public display (e.g., '+91 9876543210' -> '+91 ******3210').
    Ensures zero leak of citizen PII in public APIs.
    """
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", str(phone).strip())
    if len(cleaned) < 6:
        return "******"
    prefix = cleaned[:3] if cleaned.startswith("+") else cleaned[:2]
    suffix = cleaned[-4:]
    return f"{prefix} {'*' * (len(cleaned) - len(prefix) - 4)} {suffix}".strip()


def mask_reporter_name(name: Optional[str]) -> Optional[str]:
    """Mask citizen reporter name (e.g., 'Amit Sharma' -> 'Amit S.')."""
    if not name:
        return "Citizen Reporter"
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0][:3] + "***"
    return f"{parts[0]} {parts[-1][0]}."


def generate_report_code(row_id: int) -> str:
    """Format report sequence ID as standardized PRAVAH incident code (e.g., 'CR-1042')."""
    return f"CR-{1000 + row_id}"


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees) in kilometers.
    """
    earth_radius_km = 6371.0

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return earth_radius_km * c


def get_current_utc_iso() -> str:
    """Return standard ISO 8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()
