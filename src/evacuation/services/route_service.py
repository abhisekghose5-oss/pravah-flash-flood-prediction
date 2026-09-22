"""Database persistence for evacuation routes history."""
import json
import sqlite3
from typing import List, Dict, Optional, Any
from src.data.db import get_connection
from src.evacuation.models.route import EvacuationRoute


def init_evacuation_tables():
    """Creates SQLite tables for evacuation route history and dispatch logs."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evacuation_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT UNIQUE NOT NULL,
                origin_lat REAL NOT NULL,
                origin_lng REAL NOT NULL,
                dest_shelter_id TEXT NOT NULL,
                dest_shelter_name TEXT NOT NULL,
                distance_km REAL NOT NULL,
                travel_time_mins REAL NOT NULL,
                risk_score REAL NOT NULL,
                safety_classification TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                objective TEXT NOT NULL,
                polyline_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_evac_route_created 
            ON evacuation_routes(created_at)
        """)
        conn.commit()


def save_evacuation_route(route: EvacuationRoute) -> int:
    """Inserts a generated evacuation route record into SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO evacuation_routes (
                route_id, origin_lat, origin_lng, dest_shelter_id, dest_shelter_name,
                distance_km, travel_time_mins, risk_score, safety_classification,
                algorithm, objective, polyline_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            route.route_id,
            route.origin.get("latitude", 0.0),
            route.origin.get("longitude", 0.0),
            route.destination.get("shelter_id", ""),
            route.destination.get("name", ""),
            route.distance_km,
            route.estimated_time_minutes,
            route.risk_score,
            route.safety_classification.value,
            route.algorithm_used.value,
            route.objective.value,
            json.dumps(route.polyline),
            route.generated_at,
        ))
        conn.commit()
        return cursor.lastrowid or 0


def get_recent_evacuation_routes(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetches recent evacuation route audit records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, route_id, origin_lat, origin_lng, dest_shelter_id, dest_shelter_name,
                   distance_km, travel_time_mins, risk_score, safety_classification,
                   algorithm, objective, polyline_json, created_at
            FROM evacuation_routes
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["polyline"] = json.loads(d["polyline_json"])
            except Exception:
                d["polyline"] = []
            result.append(d)
        return result


def get_route_by_code(route_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves route record by route_id code."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, route_id, origin_lat, origin_lng, dest_shelter_id, dest_shelter_name,
                   distance_km, travel_time_mins, risk_score, safety_classification,
                   algorithm, objective, polyline_json, created_at
            FROM evacuation_routes
            WHERE route_id = ?
        """, (route_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["polyline"] = json.loads(d["polyline_json"])
        except Exception:
            d["polyline"] = []
        return d
