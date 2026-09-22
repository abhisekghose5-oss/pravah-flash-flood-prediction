"""
PRAVAH — Community Intelligence & Ground-Truth Escalation Pipeline
Provides clean, decoupled analytical interfaces for downstream PRAVAH systems
(monitoring dashboards, evacuation routing, alert advisory augmentation).
Integrates verified community ground intelligence without altering existing ML models.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from src.community.utils.helpers import haversine_distance_km

logger = logging.getLogger("pravah.community.intelligence_pipeline")


def compute_community_ground_signals(
    verified_reports: List[Dict[str, Any]],
    target_lat: Optional[float] = None,
    target_lon: Optional[float] = None,
    radius_km: float = 25.0,
    window_hours: float = 6.0,
) -> Dict[str, Any]:
    """
    Synthesize verified crowdsourced reports into ground-truth intelligence signals.

    Rules:
    - Only officially 'VERIFIED' reports are considered for situational escalation.
    - Requires temporal window match (default: past 6 hours).
    - If target_lat/target_lon specified, filters within spatial radius (default: 25 km).
    - Returns confidence score and ground-truth escalation recommendation.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    relevant_reports = []
    blocked_roads = 0
    max_depth = 0.0
    critical_count = 0

    for rep in verified_reports:
        # 1. Status Check
        if rep.get("verification_status") != "VERIFIED":
            continue

        # 2. Time Window Check
        ts_str = rep.get("reported_at", "")
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < cutoff:
                continue
        except Exception:
            continue

        # 3. Spatial Check (if target coordinates given)
        if target_lat is not None and target_lon is not None:
            rep_lat = rep.get("latitude")
            rep_lon = rep.get("longitude")
            if rep_lat is None or rep_lon is None:
                continue
            dist = haversine_distance_km(target_lat, target_lon, float(rep_lat), float(rep_lon))
            if dist > radius_km:
                continue

        relevant_reports.append(rep)

        # Metrics aggregation
        if rep.get("report_type") == "BLOCKED_ROAD":
            blocked_roads += 1

        depth = rep.get("water_depth")
        if depth and float(depth) > max_depth:
            max_depth = float(depth)

        if rep.get("severity") in ("HIGH", "CRITICAL"):
            critical_count += 1

    total_verified = len(relevant_reports)

    # Calculate ground-truth confidence boost (0.0 to 1.0)
    # 1 report = 0.35, 2 reports = 0.65, 3+ reports = 0.95
    if total_verified == 0:
        confidence = 0.0
        escalation_recommended = False
    elif total_verified == 1:
        confidence = 0.35
        escalation_recommended = (critical_count >= 1 and max_depth >= 1.0)
    elif total_verified == 2:
        confidence = 0.70
        escalation_recommended = True
    else:
        confidence = 0.95
        escalation_recommended = True

    return {
        "verified_reports_count": total_verified,
        "critical_reports_count": critical_count,
        "blocked_roads_count": blocked_roads,
        "max_reported_water_depth_meters": round(max_depth, 2),
        "ground_truth_confidence": round(confidence, 2),
        "ground_truth_escalation_signal": escalation_recommended,
        "analysis_radius_km": radius_km if target_lat is not None else "all_catchments",
        "time_window_hours": window_hours,
        "timestamp": now.isoformat(),
        "summary": (
            f"{total_verified} verified community observations in the past {int(window_hours)}h. "
            f"Blocked roads: {blocked_roads}, Max water depth: {max_depth:.1f}m."
        ),
    }
