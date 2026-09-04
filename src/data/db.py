"""
PRAVAH — SQLite Telemetry & Incident Persistence Layer
Provides crash-resilient local database persistence for:
1. Citizen emergency WhatsApp/SMS alert subscriptions
2. Crowdsourced Citizen SOS flood incident reports
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "pravah_telemetry.db"


def get_connection() -> sqlite3.Connection:
    """Establish connection to SQLite with row dictionary factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables with indexes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Subscriptions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                catchment_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_catchment ON subscriptions(catchment_id);")

        # 2. SOS Flood Reports Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sos_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                severity TEXT NOT NULL,
                severity_tier TEXT,
                landmark_notes TEXT,
                timestamp TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sos_coords ON sos_reports(latitude, longitude);")

        conn.commit()


def save_subscription(phone_number: str, catchment_id: str) -> int:
    """Insert or update a citizen alert subscription."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO subscriptions (phone_number, catchment_id, created_at)
            VALUES (?, ?, ?)
        """, (phone_number.strip(), catchment_id.strip(), now_iso))
        conn.commit()
        return cursor.lastrowid or 0


def get_all_subscriptions() -> List[Dict[str, Any]]:
    """Retrieve all registered alert subscriptions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, catchment_id, created_at FROM subscriptions ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def save_sos_report(
    latitude: float,
    longitude: float,
    severity: str,
    severity_tier: Optional[str] = None,
    landmark_notes: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> int:
    """Persist a new crowdsourced flood SOS report."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sos_reports (latitude, longitude, severity, severity_tier, landmark_notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (latitude, longitude, severity, severity_tier, landmark_notes, ts))
        conn.commit()
        return cursor.lastrowid or 0


def get_all_sos_reports() -> List[Dict[str, Any]]:
    """Retrieve all persisted SOS reports for WebGL rendering."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, latitude, longitude, severity, severity_tier, landmark_notes, timestamp
            FROM sos_reports
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# Auto-initialize tables on module import
init_db()
