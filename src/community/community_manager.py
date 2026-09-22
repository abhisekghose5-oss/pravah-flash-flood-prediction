"""
PRAVAH — Community Manager Facade
Coordinates incoming citizen reports, photo verification,
moderation workflows, and spatial intelligence queries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, UploadFile

from src.community.models.incident import (
    CommunityReportCreate,
    ReportStatus,
    StatusUpdatePayload,
)
from src.community.report_service import (
    add_photo_to_community_report,
    create_community_report,
    get_community_clusters,
    get_community_map_geojson,
    get_community_report_by_id,
    get_community_reports,
    get_community_stats,
    update_community_report_status,
)
from src.community.report_validation import validate_and_clean_report_data
from src.community.services.moderation_service import validate_status_transition
from src.community.services.photo_service import process_and_save_photo

logger = logging.getLogger("pravah.community.manager")


class CommunityManager:
    """Central orchestrator for crowdsourced flood intelligence."""

    @staticmethod
    async def submit_report(
        payload: CommunityReportCreate,
        photo_file: Optional[UploadFile] = None,
    ) -> Dict[str, Any]:
        """
        Validates, checks for duplicates, optionally saves photo,
        and persists the new report.
        """
        # 1. Clean and validate payload
        cleaned_data = validate_and_clean_report_data(payload)

        # 2. Process photo if uploaded
        photo_url = None
        if photo_file:
            photo_url = await process_and_save_photo(photo_file)

        # 3. Persist report with duplicate clustering
        report = create_community_report(cleaned_data, photo_url=photo_url)
        logger.info(
            "📢 Community report created: Code %s, Type %s, Severity %s, Photo %s",
            report["report_code"], report["report_type"], report["severity"], photo_url or "None"
        )
        return report

    @staticmethod
    def list_reports(
        report_type: Optional[str] = None,
        severity: Optional[str] = None,
        verification_status: Optional[str] = None,
        state_region: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve filtered community reports."""
        target_status = verification_status or status
        return get_community_reports(
            report_type=report_type,
            severity=severity,
            verification_status=target_status,
            state_region=state_region,
            search=search,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def get_report(report_id_or_code: str | int) -> Dict[str, Any]:
        """Retrieve report by ID or code; raises 404 if not found."""
        report = get_community_report_by_id(report_id_or_code)
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Community report '{report_id_or_code}' not found."
            )
        return report

    @staticmethod
    def update_status(report_id: int, payload: StatusUpdatePayload) -> Dict[str, Any]:
        """Validate and apply status transition."""
        existing = CommunityManager.get_report(report_id)
        current_status = existing["verification_status"]
        target_status = payload.verification_status.value

        validate_status_transition(current_status, target_status)

        updated = update_community_report_status(
            report_id=report_id,
            new_status=target_status,
            moderator_notes=payload.moderator_notes,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Report #{report_id} not found.")

        logger.info("🛡️ Report #%d status updated: %s -> %s", report_id, current_status, target_status)
        return updated

    @staticmethod
    async def add_photo(report_id: int, photo_file: UploadFile) -> Dict[str, Any]:
        """Attach an additional photo to an existing report."""
        CommunityManager.get_report(report_id)  # Validate exists
        photo_url = await process_and_save_photo(photo_file)
        if not photo_url:
            raise HTTPException(status_code=400, detail="No valid photo file provided.")

        updated = add_photo_to_community_report(report_id, photo_url)
        return updated

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Retrieve aggregated KPI counts."""
        return get_community_stats()

    @staticmethod
    def get_map_data() -> Dict[str, Any]:
        """Retrieve GeoJSON FeatureCollection."""
        return get_community_map_geojson()

    @staticmethod
    def get_clusters() -> List[Dict[str, Any]]:
        """Retrieve grouped incident clusters."""
        return get_community_clusters()
