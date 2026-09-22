"""
PRAVAH — Duplicate Report & Incident Clustering Service
Identifies spatial-temporal incident clusters from crowdsourced submissions.
Associates concurrent reports of the same event with a parent incident
while preserving every citizen submission.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from src.community.utils.helpers import haversine_distance_km

logger = logging.getLogger("pravah.community.duplicate_service")

# Clustering hyperparameters
CLUSTER_MAX_DISTANCE_KM: float = 1.0       # 1 km spatial radius
CLUSTER_MAX_TIME_HOURS: float = 2.0        # 2 hour temporal window


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse ISO timestamp string safely into UTC datetime."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def detect_duplicate_or_cluster(
    latitude: float,
    longitude: float,
    report_type: str,
    reported_at: str,
    recent_reports: List[Dict[str, Any]],
) -> Tuple[bool, Optional[int]]:
    """
    Evaluates whether an incoming submission is a duplicate/cluster of an existing report.

    Args:
        latitude: Target report latitude
        longitude: Target report longitude
        report_type: Category (e.g. 'BLOCKED_ROAD')
        reported_at: ISO timestamp of new report
        recent_reports: List of active/recent reports from database

    Returns:
        (is_duplicate, parent_incident_id)
        - If matched, returns (True, parent_id)
        - If new unique incident, returns (False, None)
    """
    new_dt = parse_timestamp(reported_at)
    if not new_dt:
        return False, None

    for existing in recent_reports:
        # 1. Type Match
        if existing.get("report_type") != report_type:
            continue

        # 2. Status check - don't cluster against rejected or resolved reports
        if existing.get("verification_status") in ("REJECTED", "RESOLVED"):
            continue

        # 3. Temporal Proximity Check
        exist_dt = parse_timestamp(existing.get("reported_at", ""))
        if not exist_dt:
            continue

        time_diff_hours = abs((new_dt - exist_dt).total_seconds()) / 3600.0
        if time_diff_hours > CLUSTER_MAX_TIME_HOURS:
            continue

        # 4. Spatial Proximity Check
        exist_lat = existing.get("latitude")
        exist_lon = existing.get("longitude")
        if exist_lat is None or exist_lon is None:
            continue

        dist_km = haversine_distance_km(latitude, longitude, float(exist_lat), float(exist_lon))
        if dist_km <= CLUSTER_MAX_DISTANCE_KM:
            parent_id = existing.get("parent_incident_id") or existing.get("id")
            logger.info(
                "🔗 Duplicate/Cluster match found! New report (lat %.4f, lon %.4f) "
                "matches report #%s (dist: %.2f km, Δt: %.1f hrs). Associating with Parent #%s.",
                latitude, longitude, existing.get("id"), dist_km, time_diff_hours, parent_id
            )
            return True, int(parent_id)

    return False, None
