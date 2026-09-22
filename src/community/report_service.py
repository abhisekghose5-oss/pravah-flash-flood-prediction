"""
PRAVAH — Community Reports Database & Persistence Service
Provides SQLite persistence, indexing, querying, and GeoJSON export for
the community reporting system in data/pravah_telemetry.db.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.community.models.incident import (
    CommunityReportResponse,
    ReportStatus,
    ReportType,
    RoadStatus,
    SeverityLevel,
)
from src.community.services.duplicate_service import detect_duplicate_or_cluster
from src.community.utils.helpers import (
    generate_report_code,
    get_current_utc_iso,
    mask_phone_number,
    mask_reporter_name,
)
from src.data.db import get_connection

logger = logging.getLogger("pravah.community.report_service")


def init_community_tables() -> None:
    """Initialize community reporting tables and indexes in SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS community_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_code TEXT UNIQUE NOT NULL,
                report_type TEXT NOT NULL,
                title TEXT,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                location_accuracy REAL,
                location_name TEXT,
                district TEXT,
                state_region TEXT,
                water_depth REAL,
                road_status TEXT,
                road_name TEXT,
                hazard_cause TEXT,
                photo_url TEXT,
                additional_photos TEXT,
                reported_at TEXT NOT NULL,
                reporter_id TEXT,
                reporter_name TEXT,
                reporter_contact TEXT,
                verification_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
                moderator_notes TEXT,
                parent_incident_id INTEGER,
                is_duplicate INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_coords ON community_reports(latitude, longitude);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_type ON community_reports(report_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_status ON community_reports(verification_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_reported ON community_reports(reported_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_parent ON community_reports(parent_incident_id);")
        conn.commit()

    seed_sample_community_reports()


def seed_sample_community_reports() -> None:
    """Seed realistic initial community reports across Maharashtra & Northeast if table is empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM community_reports")
        row = cursor.fetchone()
        if row and row["cnt"] > 0:
            return

        now = datetime.now(timezone.utc).isoformat()
        sample_reports = [
            (
                "CR-1001",
                ReportType.BLOCKED_ROAD.value,
                "NH-48 Wai Ghat Road Blocked",
                "Severe water overflow from catchment culvert has completely blocked northbound traffic on NH-48 near Wai bypass. Approximately 0.8m of fast-moving floodwater across both lanes.",
                SeverityLevel.CRITICAL.value,
                17.9482,
                73.8920,
                10.0,
                "Wai Bypass Culvert, NH-48",
                "Satara",
                "Maharashtra",
                0.8,
                RoadStatus.COMPLETELY_BLOCKED.value,
                "NH-48",
                "Flash Flood Overtopping",
                None,
                "[]",
                now,
                "CITIZEN_MH_01",
                "Ramesh Patil",
                "+919822012345",
                ReportStatus.VERIFIED.value,
                "Verified by SDRF Satara emergency field unit at 14:15 IST.",
                None,
                0,
                now,
                now,
            ),
            (
                "CR-1002",
                ReportType.FLOOD_OBSERVATION.value,
                "Market Area Inundation Mahad",
                "Savitri river overflow has submerged ground floor shops in vegetable market area. Residents moving to first floor.",
                SeverityLevel.HIGH.value,
                18.0833,
                73.4167,
                15.0,
                "Mahad Main Market Square",
                "Raigad",
                "Maharashtra",
                1.3,
                None,
                None,
                "River Overtopping",
                None,
                "[]",
                now,
                "CITIZEN_MH_02",
                "Sanjay Deshmukh",
                "+919823054321",
                ReportStatus.VERIFIED.value,
                "Confirmed via local disaster management cell.",
                None,
                0,
                now,
                now,
            ),
            (
                "CR-1003",
                ReportType.WATER_LEVEL.value,
                "Beki River Stage Observation",
                "Observed water mark reaching red benchmark pole at Beki railway bridge pier. Water is exceptionally swift.",
                SeverityLevel.HIGH.value,
                26.4983,
                90.9192,
                8.0,
                "Beki Railway Bridge Pier",
                "Barpeta",
                "Northeast",
                2.1,
                None,
                None,
                "Heavy Orographic Upstream Downpour",
                None,
                "[]",
                now,
                "CITIZEN_NE_01",
                "Bipul Das",
                "+919435012345",
                ReportStatus.VERIFIED.value,
                "Gauge observer verified reading.",
                None,
                0,
                now,
                now,
            ),
            (
                "CR-1004",
                ReportType.GENERAL_INCIDENT.value,
                "Bridge Approach Soil Erosion Dibrugarh",
                "Brahmaputra embankment near south riverbank experiencing rapid scouring and mud slip near local village road.",
                SeverityLevel.MODERATE.value,
                27.4526,
                94.8972,
                20.0,
                "Dibrugarh South Embankment",
                "Dibrugarh",
                "Northeast",
                0.4,
                RoadStatus.PARTIALLY_BLOCKED.value,
                "Embankment Link Road",
                "Bank Erosion",
                None,
                "[]",
                now,
                "CITIZEN_NE_02",
                "Anurag Saikia",
                "+919436067890",
                ReportStatus.PENDING_REVIEW.value,
                None,
                None,
                0,
                now,
                now,
            ),
        ]

        cursor.executemany("""
            INSERT INTO community_reports (
                report_code, report_type, title, description, severity,
                latitude, longitude, location_accuracy, location_name, district, state_region,
                water_depth, road_status, road_name, hazard_cause, photo_url, additional_photos,
                reported_at, reporter_id, reporter_name, reporter_contact,
                verification_status, moderator_notes, parent_incident_id, is_duplicate,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, sample_reports)
        conn.commit()
        logger.info("🌱 Seeded %d initial community reports.", len(sample_reports))


def create_community_report(report_data: Dict[str, Any], photo_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Persists a validated community report, automatically performing duplicate
    clustering and generating a unique report code.
    """
    now = get_current_utc_iso()
    lat = report_data["latitude"]
    lon = report_data["longitude"]
    rep_type = report_data["report_type"]
    reported_at = report_data.get("reported_at") or now

    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Fetch recent reports for duplicate/cluster detection
        cursor.execute("""
            SELECT id, report_type, latitude, longitude, reported_at, verification_status, parent_incident_id
            FROM community_reports
            ORDER BY id DESC
            LIMIT 100;
        """)
        recent_rows = [dict(r) for r in cursor.fetchall()]

        is_dup, parent_id = detect_duplicate_or_cluster(
            latitude=lat,
            longitude=lon,
            report_type=rep_type,
            reported_at=reported_at,
            recent_reports=recent_rows,
        )

        # 2. Insert temporary record to get auto-increment row ID
        placeholder_code = f"CR-PENDING-{datetime.now().timestamp()}"
        cursor.execute("""
            INSERT INTO community_reports (
                report_code, report_type, title, description, severity,
                latitude, longitude, location_accuracy, location_name, district, state_region,
                water_depth, road_status, road_name, hazard_cause, photo_url, additional_photos,
                reported_at, reporter_id, reporter_name, reporter_contact,
                verification_status, moderator_notes, parent_incident_id, is_duplicate,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            placeholder_code,
            rep_type,
            f"{rep_type.replace('_', ' ').title()} - {report_data.get('location_name') or 'Incident'}",
            report_data["description"],
            report_data["severity"],
            lat,
            lon,
            report_data.get("location_accuracy"),
            report_data.get("location_name"),
            report_data.get("district"),
            report_data.get("state_region"),
            report_data.get("water_depth"),
            report_data.get("road_status"),
            report_data.get("road_name"),
            report_data.get("hazard_cause"),
            photo_url,
            "[]",
            reported_at,
            f"CITIZEN_{int(datetime.now().timestamp())}",
            report_data.get("reporter_name"),
            report_data.get("reporter_contact"),
            ReportStatus.PENDING_REVIEW.value,
            None,
            parent_id,
            1 if is_dup else 0,
            now,
            now,
        ))
        row_id = cursor.lastrowid or 0

        # 3. Update unique standardized code (CR-1000+)
        final_code = generate_report_code(row_id)
        cursor.execute("UPDATE community_reports SET report_code = ? WHERE id = ?", (final_code, row_id))
        conn.commit()

        # 4. Return formatted record
        cursor.execute("SELECT * FROM community_reports WHERE id = ?", (row_id,))
        row = cursor.fetchone()
        return format_report_row(dict(row), conn=conn)


def format_report_row(row: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Convert raw SQLite row dict to public-safe CommunityReportResponse format."""
    rep_id = row["id"]
    parent_id = row.get("parent_incident_id")

    # Determine cluster sibling count
    cluster_count = 1
    if parent_id or not row.get("is_duplicate"):
        root_id = parent_id or rep_id
        try:
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM community_reports WHERE id = ? OR parent_incident_id = ?",
                    (root_id, root_id)
                )
                cnt_row = cursor.fetchone()
                if cnt_row:
                    cluster_count = cnt_row["cnt"]
            else:
                with get_connection() as c:
                    cur = c.cursor()
                    cur.execute(
                        "SELECT COUNT(*) as cnt FROM community_reports WHERE id = ? OR parent_incident_id = ?",
                        (root_id, root_id)
                    )
                    cnt_row = cur.fetchone()
                    if cnt_row:
                        cluster_count = cnt_row["cnt"]
        except Exception:
            cluster_count = 1

    # Additional photos array
    add_photos = []
    if row.get("additional_photos"):
        try:
            add_photos = json.loads(row["additional_photos"])
        except Exception:
            add_photos = []

    # Mask reporter name
    masked_name = mask_reporter_name(row.get("reporter_name"))

    return {
        "id": rep_id,
        "report_code": row["report_code"],
        "report_type": row["report_type"],
        "title": row.get("title") or f"{row['report_type'].replace('_', ' ').title()}",
        "description": row["description"],
        "severity": row["severity"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "location_accuracy": row.get("location_accuracy"),
        "location_name": row.get("location_name"),
        "district": row.get("district"),
        "state_region": row.get("state_region"),
        "water_depth": row.get("water_depth"),
        "road_status": row.get("road_status"),
        "road_name": row.get("road_name"),
        "hazard_cause": row.get("hazard_cause"),
        "photo_url": row.get("photo_url"),
        "additional_photos": add_photos,
        "reported_at": row["reported_at"],
        "verification_status": row["verification_status"],
        "is_verified": (row["verification_status"] == ReportStatus.VERIFIED.value),
        "is_duplicate": bool(row.get("is_duplicate")),
        "parent_incident_id": parent_id,
        "cluster_count": cluster_count,
        "reporter_display": masked_name,
        "moderator_notes": row.get("moderator_notes"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_community_reports(
    report_type: Optional[str] = None,
    severity: Optional[str] = None,
    verification_status: Optional[str] = None,
    state_region: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve community reports with flexible filtering and pagination."""
    query = "SELECT * FROM community_reports WHERE 1=1"
    params: List[Any] = []

    if report_type:
        query += " AND report_type = ?"
        params.append(report_type)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if verification_status:
        query += " AND verification_status = ?"
        params.append(verification_status)
    if state_region:
        query += " AND (state_region = ? OR state_region LIKE ?)"
        params.append(state_region)
        params.append(f"%{state_region}%")
    if search:
        query += " AND (description LIKE ? OR location_name LIKE ? OR road_name LIKE ? OR report_code LIKE ?)"
        s = f"%{search.strip()}%"
        params.extend([s, s, s, s])

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [format_report_row(dict(r), conn=conn) for r in rows]


def get_community_report_by_id(identifier: str | int) -> Optional[Dict[str, Any]]:
    """Retrieve a single report by ID (e.g. 1) or report code (e.g. 'CR-1001')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if str(identifier).isdigit():
            cursor.execute("SELECT * FROM community_reports WHERE id = ?", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM community_reports WHERE report_code = ?", (str(identifier),))

        row = cursor.fetchone()
        if not row:
            return None
        return format_report_row(dict(row), conn=conn)


def update_community_report_status(
    report_id: int,
    new_status: str,
    moderator_notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update moderation/verification lifecycle status for a report."""
    now = get_current_utc_iso()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM community_reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        if not row:
            return None

        cursor.execute("""
            UPDATE community_reports
            SET verification_status = ?, moderator_notes = ?, updated_at = ?
            WHERE id = ?;
        """, (new_status, moderator_notes or row["moderator_notes"], now, report_id))
        conn.commit()

        cursor.execute("SELECT * FROM community_reports WHERE id = ?", (report_id,))
        updated_row = cursor.fetchone()
        return format_report_row(dict(updated_row), conn=conn)


def add_photo_to_community_report(report_id: int, new_photo_url: str) -> Optional[Dict[str, Any]]:
    """Attach an additional photo URL to an existing report."""
    now = get_current_utc_iso()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT photo_url, additional_photos FROM community_reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        if not row:
            return None

        primary_photo = row["photo_url"]
        add_photos = []
        if row["additional_photos"]:
            try:
                add_photos = json.loads(row["additional_photos"])
            except Exception:
                add_photos = []

        if not primary_photo:
            primary_photo = new_photo_url
        else:
            add_photos.append(new_photo_url)

        cursor.execute("""
            UPDATE community_reports
            SET photo_url = ?, additional_photos = ?, updated_at = ?
            WHERE id = ?;
        """, (primary_photo, json.dumps(add_photos), now, report_id))
        conn.commit()

        cursor.execute("SELECT * FROM community_reports WHERE id = ?", (report_id,))
        updated_row = cursor.fetchone()
        return format_report_row(dict(updated_row), conn=conn)


def get_community_stats() -> Dict[str, Any]:
    """Calculate aggregate summary KPIs for the community dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM community_reports;")
        total = cursor.fetchone()["total"]

        # Today's date prefix
        today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) as today FROM community_reports WHERE reported_at LIKE ?;", (f"{today_prefix}%",))
        reports_today = cursor.fetchone()["today"]

        cursor.execute("SELECT COUNT(*) as pending FROM community_reports WHERE verification_status = 'PENDING_REVIEW' OR verification_status = 'SUBMITTED';")
        pending = cursor.fetchone()["pending"]

        cursor.execute("SELECT COUNT(*) as verified FROM community_reports WHERE verification_status = 'VERIFIED';")
        verified = cursor.fetchone()["verified"]

        cursor.execute("SELECT COUNT(*) as blocked FROM community_reports WHERE report_type = 'BLOCKED_ROAD' AND (road_status = 'COMPLETELY_BLOCKED' OR road_status = 'PARTIALLY_BLOCKED') AND verification_status != 'RESOLVED' AND verification_status != 'REJECTED';")
        blocked = cursor.fetchone()["blocked"]

        cursor.execute("SELECT COUNT(*) as active FROM community_reports WHERE verification_status != 'RESOLVED' AND verification_status != 'REJECTED';")
        active = cursor.fetchone()["active"]

        return {
            "total_reports": total,
            "reports_today": reports_today,
            "pending_verification": pending,
            "verified_reports": verified,
            "blocked_roads": blocked,
            "active_incidents": active,
            "timestamp": get_current_utc_iso(),
        }


def get_community_map_geojson() -> Dict[str, Any]:
    """
    Export active community reports as a standard GeoJSON FeatureCollection
    for direct Leaflet/MapLibre GIS rendering.
    """
    reports = get_community_reports(limit=500)
    features = []

    for r in reports:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["longitude"], r["latitude"]],
            },
            "properties": {
                "id": r["id"],
                "report_code": r["report_code"],
                "report_type": r["report_type"],
                "title": r["title"],
                "description": r["description"],
                "severity": r["severity"],
                "location_name": r["location_name"],
                "district": r["district"],
                "state_region": r["state_region"],
                "water_depth": r["water_depth"],
                "road_status": r["road_status"],
                "road_name": r["road_name"],
                "photo_url": r["photo_url"],
                "reported_at": r["reported_at"],
                "verification_status": r["verification_status"],
                "is_verified": r["is_verified"],
                "cluster_count": r["cluster_count"],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def get_community_clusters() -> List[Dict[str, Any]]:
    """Retrieve grouped incident clusters and their member citizen reports."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Find root reports that either have child reports or are distinct
        cursor.execute("""
            SELECT id, report_code, report_type, severity, latitude, longitude, location_name, reported_at
            FROM community_reports
            WHERE parent_incident_id IS NULL
            ORDER BY id DESC;
        """)
        roots = cursor.fetchall()
        clusters = []

        for root in roots:
            root_id = root["id"]
            cursor.execute("""
                SELECT * FROM community_reports
                WHERE id = ? OR parent_incident_id = ?
                ORDER BY id ASC;
            """, (root_id, root_id))
            members = cursor.fetchall()

            clusters.append({
                "cluster_id": root_id,
                "primary_code": root["report_code"],
                "report_type": root["report_type"],
                "severity": root["severity"],
                "latitude": root["latitude"],
                "longitude": root["longitude"],
                "location_name": root["location_name"],
                "child_count": len(members),
                "latest_reported_at": members[-1]["reported_at"] if members else root["reported_at"],
                "reports": [format_report_row(dict(m), conn=conn) for m in members],
            })

        return clusters
