"""
PRAVAH — Multi-Channel Alert Database & Persistence Service
Persists alert events and per-channel delivery statuses to SQLite (data/pravah_telemetry.db).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.alerts.models.alert import (
    AlertRecordResponse,
    AlertSeverity,
    ChannelDeliveryDetail,
    DeliveryStatus,
)
from src.alerts.utils.helpers import generate_alert_code, get_current_utc_iso
from src.data.db import get_connection

logger = logging.getLogger("pravah.alerts.service")


def init_alert_tables() -> None:
    """Initialize multi-channel alerting tables and indexes in SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS multi_channel_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_code TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                location TEXT NOT NULL,
                region TEXT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                trigger_reason TEXT NOT NULL,
                risk_score REAL,
                river_level REAL,
                river_threshold REAL,
                rainfall_forecast REAL,
                evacuation_route TEXT,
                shelter_location TEXT,
                overall_status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_ts ON multi_channel_alerts(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_sev ON multi_channel_alerts(severity);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_loc ON multi_channel_alerts(location);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_channel_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                recipient TEXT NOT NULL,
                delivery_status TEXT NOT NULL,
                message_id TEXT,
                provider_response TEXT,
                error_message TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (alert_id) REFERENCES multi_channel_alerts(id)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_alert ON alert_channel_deliveries(alert_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_chan ON alert_channel_deliveries(channel);")
        conn.commit()

    seed_sample_alerts()


def seed_sample_alerts() -> None:
    """Seed realistic initial alert records across Maharashtra & Northeast if table empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM multi_channel_alerts")
        row = cursor.fetchone()
        if row and row["cnt"] > 0:
            return

        now = get_current_utc_iso()
        sample_alerts = [
            (
                "ALT-1001",
                now,
                "Mahad",
                "Maharashtra",
                "RIVER_LEVEL",
                AlertSeverity.CRITICAL.value,
                "River level (9.2m) exceeded critical danger stage (9.0m) • AI flood onset risk (88%) reached critical danger tier",
                88.0,
                9.2,
                9.0,
                210.0,
                "SH-72 towards Mahad High Ridge Bypass",
                "Mahad Flood Evacuation Center & SDRF Staging Base",
                "DELIVERED",
                now,
            ),
            (
                "ALT-1002",
                now,
                "Beki",
                "Northeast",
                "MULTI_FACTOR",
                AlertSeverity.EVACUATION.value,
                "River level (9.6m) breached catastrophic evacuation mark • Severe orographic downpour upstream",
                94.0,
                9.6,
                9.0,
                240.0,
                "NH-31 High-Ground Corridor towards Barpeta Road",
                "Barpeta Multi-Purpose Cyclone & Flood Shelter",
                "DELIVERED",
                now,
            ),
            (
                "ALT-1003",
                now,
                "Karad",
                "Maharashtra",
                "RISK_SCORE",
                AlertSeverity.WARNING.value,
                "AI flood onset risk (74%) exceeded alert threshold (70%) • Heavy precipitation active in Western Ghats headwaters",
                74.0,
                8.1,
                8.0,
                160.0,
                "NH-48 Elevated Flyover Corridor",
                "Karad Municipal High Ground Disaster Staging Hall",
                "DELIVERED",
                now,
            ),
        ]

        cursor.executemany("""
            INSERT INTO multi_channel_alerts (
                alert_code, timestamp, location, region, alert_type, severity,
                trigger_reason, risk_score, river_level, river_threshold,
                rainfall_forecast, evacuation_route, shelter_location,
                overall_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, sample_alerts)
        conn.commit()

        # Seed deliveries for sample alerts
        deliveries = [
            # ALT-1001 Deliveries
            (1, "sms", "+91 ******2345", DeliveryStatus.DELIVERED.value, "SMS_SIM_101", "Simulated SMS cellular dispatch", None, now),
            (1, "whatsapp", "+91 ******2345", DeliveryStatus.DELIVERED.value, "WA_SIM_101", "Simulated WhatsApp delivery", None, now),
            (1, "telegram", "@pravah_alerts", DeliveryStatus.DELIVERED.value, "TG_SIM_101", "Telegram broadcast confirmed", None, now),
            # ALT-1002 Deliveries
            (2, "sms", "+91 ******5432", DeliveryStatus.DELIVERED.value, "SMS_SIM_102", "Simulated SMS cellular dispatch", None, now),
            (2, "whatsapp", "+91 ******5432", DeliveryStatus.DELIVERED.value, "WA_SIM_102", "Simulated WhatsApp delivery", None, now),
            (2, "telegram", "@pravah_alerts", DeliveryStatus.DELIVERED.value, "TG_SIM_102", "Telegram broadcast confirmed", None, now),
            # ALT-1003 Deliveries
            (3, "sms", "+91 ******9999", DeliveryStatus.DELIVERED.value, "SMS_SIM_103", "Simulated SMS cellular dispatch", None, now),
            (3, "whatsapp", "+91 ******9999", DeliveryStatus.DELIVERED.value, "WA_SIM_103", "Simulated WhatsApp delivery", None, now),
            (3, "telegram", "@pravah_alerts", DeliveryStatus.DELIVERED.value, "TG_SIM_103", "Telegram broadcast confirmed", None, now),
        ]

        cursor.executemany("""
            INSERT INTO alert_channel_deliveries (
                alert_id, channel, recipient, delivery_status,
                message_id, provider_response, error_message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, deliveries)
        conn.commit()
        logger.info("🌱 Seeded %d initial multi-channel alerts.", len(sample_alerts))


def save_alert_record(
    location: str,
    region: Optional[str],
    alert_type: str,
    severity: str,
    trigger_reason: str,
    risk_score: Optional[float],
    river_level: Optional[float],
    river_threshold: Optional[float],
    rainfall_forecast: Optional[float],
    evacuation_route: Optional[str],
    shelter_location: Optional[str],
    overall_status: str,
    timestamp: Optional[str] = None,
) -> int:
    """Inserts a new alert event and generates an official code (ALT-1000+)."""
    now = timestamp or get_current_utc_iso()
    with get_connection() as conn:
        cursor = conn.cursor()
        placeholder_code = f"ALT-PENDING-{datetime.now().timestamp()}"
        cursor.execute("""
            INSERT INTO multi_channel_alerts (
                alert_code, timestamp, location, region, alert_type, severity,
                trigger_reason, risk_score, river_level, river_threshold,
                rainfall_forecast, evacuation_route, shelter_location,
                overall_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            placeholder_code, now, location, region or "Maharashtra", alert_type, severity,
            trigger_reason, risk_score, river_level, river_threshold,
            rainfall_forecast, evacuation_route, shelter_location,
            overall_status, now
        ))
        row_id = cursor.lastrowid or 0
        final_code = generate_alert_code(row_id)
        cursor.execute("UPDATE multi_channel_alerts SET alert_code = ? WHERE id = ?", (final_code, row_id))
        conn.commit()
        return row_id


def save_channel_delivery(
    alert_id: int,
    delivery: ChannelDeliveryDetail,
) -> None:
    """Records delivery status for an individual channel dispatch."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alert_channel_deliveries (
                alert_id, channel, recipient, delivery_status,
                message_id, provider_response, error_message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            alert_id, delivery.channel, delivery.recipient, delivery.delivery_status,
            delivery.message_id, delivery.provider_response, delivery.error_message, delivery.timestamp
        ))
        conn.commit()


def get_alerts_history(
    severity: Optional[str] = None,
    channel: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieves alert records with their associated channel delivery statuses."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM multi_channel_alerts WHERE 1=1"
        params: List[Any] = []

        if severity:
            query += " AND severity = ?"
            params.append(severity.upper())
        if location:
            query += " AND location LIKE ?"
            params.append(f"%{location}%")
        if status:
            query += " AND overall_status = ?"
            params.append(status.upper())

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        alert_rows = cursor.fetchall()

        results = []
        for a in alert_rows:
            a_dict = dict(a)
            alert_id = a_dict["id"]

            # Fetch channel deliveries
            cursor.execute("""
                SELECT channel, recipient, delivery_status, message_id, provider_response, error_message, timestamp
                FROM alert_channel_deliveries
                WHERE alert_id = ?
            """, (alert_id,))
            deliv_rows = cursor.fetchall()

            # If channel filter specified, check if alert has this channel
            delivs = [dict(d) for d in deliv_rows]
            if channel and not any(d["channel"].lower() == channel.lower() for d in delivs):
                continue

            a_dict["channels"] = delivs
            results.append(a_dict)

        return results


def get_alert_by_id(identifier: str | int) -> Optional[Dict[str, Any]]:
    """Fetch single alert by numeric ID or code."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if str(identifier).isdigit():
            cursor.execute("SELECT * FROM multi_channel_alerts WHERE id = ?", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM multi_channel_alerts WHERE alert_code = ?", (str(identifier),))

        row = cursor.fetchone()
        if not row:
            return None

        a_dict = dict(row)
        cursor.execute("""
            SELECT channel, recipient, delivery_status, message_id, provider_response, error_message, timestamp
            FROM alert_channel_deliveries
            WHERE alert_id = ?
        """, (a_dict["id"],))
        a_dict["channels"] = [dict(d) for d in cursor.fetchall()]
        return a_dict


def get_last_alert_time(location: str, severity: str) -> Optional[datetime]:
    """Retrieve timestamp of most recent alert for a specific location and severity (cooldown check)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp FROM multi_channel_alerts
            WHERE location = ? AND severity = ?
            ORDER BY id DESC LIMIT 1;
        """, (location, severity))
        row = cursor.fetchone()
        if not row:
            return None
        try:
            return datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        except Exception:
            return None


def get_alert_statistics() -> Dict[str, Any]:
    """Computes summary KPI counters for the Alerts Center dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM multi_channel_alerts;")
        total = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM multi_channel_alerts WHERE severity = 'CRITICAL';")
        critical = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM multi_channel_alerts WHERE severity = 'WARNING';")
        warning = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM multi_channel_alerts WHERE severity = 'EVACUATION';")
        evacuation = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM alert_channel_deliveries WHERE delivery_status IN ('SENT', 'DELIVERED');")
        success = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM alert_channel_deliveries WHERE delivery_status = 'FAILED';")
        failed = cursor.fetchone()["cnt"]

        return {
            "total_alerts": total,
            "critical_alerts": critical,
            "warnings": warning,
            "evacuation_alerts": evacuation,
            "successful_deliveries": success,
            "failed_deliveries": failed,
            "timestamp": get_current_utc_iso(),
        }
