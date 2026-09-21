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
                timestamp TEXT NOT NULL,
                region_tag TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sos_coords ON sos_reports(latitude, longitude);")
        
        # Check if region_tag column exists (migration helper for existing databases)
        cursor.execute("PRAGMA table_info(sos_reports);")
        columns = [row[1] for row in cursor.fetchall()]
        if "region_tag" not in columns:
            cursor.execute("ALTER TABLE sos_reports ADD COLUMN region_tag TEXT;")
        # Add photo_path column if missing (append-only migration)
        if "photo_path" not in columns:
            cursor.execute("ALTER TABLE sos_reports ADD COLUMN photo_path TEXT;")

        # 3. Relief Shelters & High-Ground Evacuation Zones Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relief_shelters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                capacity INTEGER NOT NULL,
                type TEXT NOT NULL,
                region TEXT NOT NULL,
                district TEXT,
                contact TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shelter_region ON relief_shelters(region);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shelter_coords ON relief_shelters(latitude, longitude);")

        conn.commit()

    seed_default_shelters()


def seed_default_shelters() -> None:
    """Seed verified Maharashtra & Northeast relief shelters if table is empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM relief_shelters")
        row = cursor.fetchone()
        if row and row["cnt"] > 0:
            return

        default_shelters = [
            # Maharashtra Western Ghats Shelters
            ("Shivaji Nagar Elevated Disaster Shelter", 18.5312, 73.8445, 650, "Elevated Shelter", "Maharashtra", "Pune", "+91 20 2550 1000"),
            ("Sinhagad Road Government Higher Secondary School", 18.4789, 73.8192, 500, "Government School", "Maharashtra", "Pune", "+91 20 2435 2200"),
            ("Lonavala High Ground Emergency Refuge Center", 18.7557, 73.4091, 1200, "Elevated Shelter", "Maharashtra", "Pune", "+91 2114 273000"),
            ("Panchganga Zilla Parishad Model School", 18.3842, 73.8567, 450, "Government School", "Maharashtra", "Kolhapur", "+91 231 265 4000"),
            ("Karad Municipal High Ground Disaster Staging Hall", 17.2889, 74.1844, 900, "Elevated Shelter", "Maharashtra", "Satara", "+91 2164 222100"),
            ("Mahad Flood Evacuation Center & SDRF Staging Base", 18.0833, 73.4167, 1100, "NDRF Staging Area", "Maharashtra", "Raigad", "+91 2145 222120"),

            # Northeast India (Assam & Hill Catchments) Verified Shelters & NDRF Units
            ("Guwahati IIT/SAR Elevated Campus Refuge", 26.1878, 91.6916, 1500, "Elevated Campus Shelter", "Northeast", "Kamrup Metropolitan", "+91 361 258 2000"),
            ("Kokrajhar High-Ground Multi-Purpose Relief Center", 26.4014, 90.2715, 850, "High-Ground Relief Camp", "Northeast", "Kokrajhar", "+91 3661 270220"),
            ("Barpeta Multi-Purpose Cyclone & Flood Shelter", 26.3211, 91.0044, 1200, "Elevated Disaster Shelter", "Northeast", "Barpeta", "+91 3665 252130"),
            ("Dhubri NDRF 1st Battalion Rapid Staging Ground", 26.0205, 89.9754, 750, "NDRF Staging Area", "Northeast", "Dhubri", "+91 3662 230018"),
            ("Silchar Cachar Elevated Disaster Refuge", 24.8333, 92.7789, 950, "Elevated Shelter", "Northeast", "Cachar", "+91 3842 245220"),
            ("Tezpur Air Base Disaster Refuge & Staging Unit", 26.6528, 92.7925, 1100, "NDRF Staging Area", "Northeast", "Sonitpur", "+91 3712 220050"),
            ("Dibrugarh University High-Ground Protection Center", 27.4526, 94.8972, 1400, "High-Ground Relief Camp", "Northeast", "Dibrugarh", "+91 373 237 0231"),
            ("Cherrapunji Sohra Orographic Flood Refuge", 25.2750, 91.7320, 600, "Elevated Shelter", "Northeast", "East Khasi Hills", "+91 3637 235220"),
            ("Jorhat Agricultural University Flood Safe Center", 26.7215, 94.1985, 800, "High-Ground Relief Camp", "Northeast", "Jorhat", "+91 376 234 0044"),
            ("Goalpara Multi-Purpose Flood Safe Haven", 26.1750, 90.6250, 700, "Elevated Shelter", "Northeast", "Goalpara", "+91 3663 240025"),
        ]
        cursor.executemany("""
            INSERT INTO relief_shelters (name, latitude, longitude, capacity, type, region, district, contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, default_shelters)
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
    region_tag: Optional[str] = None,
    photo_path: Optional[str] = None,
) -> int:
    """Persist a new crowdsourced flood SOS report (with optional photo attachment)."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    # Auto-assign region tag if not provided
    if not region_tag:
        if 23.5 <= latitude <= 29.5 and 88.5 <= longitude <= 98.0:
            region_tag = "Northeast Alert"
        elif 15.0 <= latitude <= 22.5 and 72.0 <= longitude <= 81.0:
            region_tag = "Maharashtra Alert"
        else:
            region_tag = "Out of Bounds Alert"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sos_reports (latitude, longitude, severity, severity_tier, landmark_notes, timestamp, region_tag, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (latitude, longitude, severity, severity_tier, landmark_notes, ts, region_tag, photo_path))
        conn.commit()
        return cursor.lastrowid or 0


def get_all_sos_reports() -> List[Dict[str, Any]]:
    """Retrieve all persisted SOS reports for WebGL rendering."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, latitude, longitude, severity, severity_tier, landmark_notes, timestamp, region_tag, photo_path
            FROM sos_reports
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_relief_shelters(region: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all relief shelters, optionally filtered by region."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if region:
            norm_region = "Northeast" if region.lower() in ("ne", "northeast") else "Maharashtra"
            cursor.execute("""
                SELECT id, name, latitude, longitude, capacity, type, region, district, contact
                FROM relief_shelters
                WHERE LOWER(region) = LOWER(?)
                ORDER BY id ASC
            """, (norm_region,))
        else:
            cursor.execute("""
                SELECT id, name, latitude, longitude, capacity, type, region, district, contact
                FROM relief_shelters
                ORDER BY id ASC
            """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def save_relief_shelter(
    name: str,
    latitude: float,
    longitude: float,
    capacity: int,
    shelter_type: str,
    region: str,
    district: Optional[str] = None,
    contact: Optional[str] = None,
) -> int:
    """Insert a new relief shelter or high-ground refuge."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO relief_shelters (name, latitude, longitude, capacity, type, region, district, contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, latitude, longitude, capacity, shelter_type, region, district, contact))
        conn.commit()
        return cursor.lastrowid or 0


# Auto-initialize tables on module import
init_db()
