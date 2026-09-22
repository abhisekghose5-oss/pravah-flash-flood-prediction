"""
PRAVAH — Community Report Moderation & Lifecycle Service
Enforces valid status transitions for crowdsourced reports:
SUBMITTED -> PENDING_REVIEW -> VERIFIED / REJECTED -> RESOLVED
"""

from __future__ import annotations

import logging
from typing import Dict, Set
from fastapi import HTTPException
from src.community.models.incident import ReportStatus

logger = logging.getLogger("pravah.community.moderation_service")

# Permitted state transitions
ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    ReportStatus.SUBMITTED.value: {
        ReportStatus.PENDING_REVIEW.value,
        ReportStatus.VERIFIED.value,
        ReportStatus.REJECTED.value,
    },
    ReportStatus.PENDING_REVIEW.value: {
        ReportStatus.VERIFIED.value,
        ReportStatus.REJECTED.value,
        ReportStatus.RESOLVED.value,
    },
    ReportStatus.VERIFIED.value: {
        ReportStatus.RESOLVED.value,
        ReportStatus.REJECTED.value,
        ReportStatus.PENDING_REVIEW.value,
    },
    ReportStatus.REJECTED.value: {
        ReportStatus.PENDING_REVIEW.value,
    },
    ReportStatus.RESOLVED.value: {
        ReportStatus.PENDING_REVIEW.value,
        ReportStatus.VERIFIED.value,
    },
}


def validate_status_transition(current_status: str, target_status: str) -> None:
    """
    Ensure the requested status transition conforms to the moderation lifecycle.
    Raises HTTPException 400 if the transition is prohibited.
    """
    if current_status == target_status:
        return

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid lifecycle transition from '{current_status}' to '{target_status}'. "
                f"Permitted next states: {sorted(list(allowed)) or 'None'}"
            ),
        )
