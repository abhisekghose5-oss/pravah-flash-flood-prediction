"""
PRAVAH — River Gauge Monitoring Service.
Provides hydrometric river-level observations, warning and danger threshold monitoring,
24-hour stage rate-of-rise trend analysis, and persistent telemetry logging.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3
import threading

from src.data.db import get_connection
from src.gauges.models.gauge import (
    RiverGauge,
    RiverGaugeHistoryPoint,
    RiverGaugeStatus,
    RiverTrend,
    ThresholdEvaluationResult,
)

logger = logging.getLogger("pravah.gauges.service")
REPO_ROOT = Path(__file__).resolve().parents[2]


class GaugeService:
    """
    Central hydrometric monitoring service managing CWC and Northeast river gauges.
    Thread-safe singleton with local SQLite persistence.
    """

    def __init__(self):
        self._gauges: Dict[str, Dict[str, Any]] = {}
        self._history_cache: Dict[str, List[RiverGaugeHistoryPoint]] = {}
        self._lock = threading.Lock()
        self._load_gauges()

    def _load_gauges(self) -> None:
        """Load static metadata for Maharashtra and Northeast river gauges."""
        # 1. Load Maharashtra Western Ghats CWC Gauges
        meta_csv = REPO_ROOT / "data" / "processed" / "target_metadata.csv"
        if meta_csv.exists():
            try:
                with open(meta_csv, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        gid = row.get("GaugeID", "").strip()
                        clean_id = gid.replace("INDOFLOODS-gauge-", "").strip()
                        station = row.get("Station", f"Station-{clean_id}").strip()
                        river = row.get("River Name/ Tributory/ SubTributory", "Krishna Basin").strip()
                        basin = row.get("Basin", "Krishna").strip()
                        lat = float(row.get("Latitude") or 17.5)
                        lon = float(row.get("Longitude") or 74.0)
                        warn_lvl = float(row.get("Warning Level") or 10.0)
                        danger_lvl = float(row.get("Danger Level") or (warn_lvl + 2.0))

                        # Initial baseline reading (normal conditions ~85% of warning)
                        curr_lvl = round(warn_lvl * 0.82, 2)

                        gauge_dict = {
                            "gauge_id": gid,
                            "clean_id": clean_id,
                            "station_name": station,
                            "river_name": river,
                            "basin_name": basin,
                            "state": "Maharashtra",
                            "region": "Maharashtra",
                            "latitude": lat,
                            "longitude": lon,
                            "current_level_m": curr_lvl,
                            "warning_level_m": warn_lvl,
                            "danger_level_m": danger_lvl,
                            "status": RiverGaugeStatus.NORMAL,
                            "trend_24h": RiverTrend.STABLE,
                            "delta_24h_m": 0.05,
                            "last_observation_utc": datetime.now(timezone.utc).isoformat(),
                        }
                        self._gauges[gid] = gauge_dict
                        self._gauges[clean_id] = gauge_dict
                logger.info("Loaded %d Maharashtra CWC gauges from %s", len(self._gauges) // 2, meta_csv.name)
            except Exception as exc:
                logger.error("Error loading Maharashtra metadata: %s", exc)

        # 2. Load Northeast India Gauges
        ne_csv = REPO_ROOT / "data" / "processed" / "northeast" / "station_catalog.csv"
        if ne_csv.exists():
            try:
                with open(ne_csv, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        st_id = row.get("StationID", "").strip()
                        if not st_id:
                            continue
                        name = row.get("Station", st_id).strip()
                        lat = float(row.get("Latitude") or 26.2)
                        lon = float(row.get("Longitude") or 92.5)
                        warn_lvl = 48.0
                        danger_lvl = 50.0
                        curr_lvl = 44.5

                        gauge_dict = {
                            "gauge_id": f"NE-{st_id}",
                            "clean_id": st_id,
                            "station_name": name,
                            "river_name": "Brahmaputra Basin",
                            "basin_name": "Brahmaputra",
                            "state": row.get("State", "Assam").strip(),
                            "region": "Northeast",
                            "latitude": lat,
                            "longitude": lon,
                            "current_level_m": curr_lvl,
                            "warning_level_m": warn_lvl,
                            "danger_level_m": danger_lvl,
                            "status": RiverGaugeStatus.NORMAL,
                            "trend_24h": RiverTrend.STABLE,
                            "delta_24h_m": 0.1,
                            "last_observation_utc": datetime.now(timezone.utc).isoformat(),
                        }
                        self._gauges[f"NE-{st_id}"] = gauge_dict
                        self._gauges[st_id] = gauge_dict
                logger.info("Loaded Northeast gauges catalog from %s", ne_csv.name)
            except Exception as exc:
                logger.error("Error loading Northeast catalog: %s", exc)

    def _normalize_id(self, gauge_id: str) -> str:
        """Normalize gauge identifier string."""
        gid = str(gauge_id).strip()
        if gid in self._gauges:
            return self._gauges[gid]["gauge_id"]
        # Try clean ID
        clean = gid.replace("INDOFLOODS-gauge-", "").replace("NE-", "").strip()
        if clean in self._gauges:
            return self._gauges[clean]["gauge_id"]
        return gid

    def get_gauge(self, gauge_id: str) -> Optional[RiverGauge]:
        """Retrieve full details and live status for a specific gauge."""
        norm = self._normalize_id(gauge_id)
        with self._lock:
            g = self._gauges.get(norm)
            if not g:
                return None
            return RiverGauge(**g)

    def list_gauges(
        self,
        region: Optional[str] = None,
        status: Optional[RiverGaugeStatus] = None,
    ) -> List[RiverGauge]:
        """List monitored gauges with optional regional and status filtering."""
        with self._lock:
            # Gather unique gauges
            seen = set()
            unique = []
            for g in self._gauges.values():
                gid = g["gauge_id"]
                if gid not in seen:
                    seen.add(gid)
                    unique.append(g)

        result = []
        for g in unique:
            if region and g["region"].lower() != region.lower():
                continue
            if status and g["status"] != status:
                continue
            result.append(RiverGauge(**g))

        return sorted(result, key=lambda x: (x.region, x.station_name))

    def evaluate_threshold(
        self,
        gauge_id: str,
        simulated_level_m: Optional[float] = None,
    ) -> ThresholdEvaluationResult:
        """
        Evaluate gauge river level against warning and danger thresholds.
        """
        norm = self._normalize_id(gauge_id)
        with self._lock:
            g = self._gauges.get(norm)
            if not g:
                raise ValueError(f"Gauge '{gauge_id}' not found")

            lvl = simulated_level_m if simulated_level_m is not None else g["current_level_m"]
            warn_lvl = g["warning_level_m"]
            danger_lvl = g["danger_level_m"]
            station = g["station_name"]
            river = g["river_name"]

        head_warn = round(lvl - warn_lvl, 2)
        head_danger = round(lvl - danger_lvl, 2)

        if lvl >= danger_lvl:
            st = RiverGaugeStatus.DANGER
            exceeded = True
            sev = "EVACUATION" if (lvl >= danger_lvl + 1.0) else "CRITICAL"
            action = f"Danger Mark Breached (+{head_danger}m). Issue immediate public emergency evacuation directive."
        elif lvl >= warn_lvl:
            st = RiverGaugeStatus.WARNING
            exceeded = True
            sev = "WARNING"
            action = f"Warning Level Exceeded (+{head_warn}m). Place riverine emergency rescue units on standby."
        else:
            st = RiverGaugeStatus.NORMAL
            exceeded = False
            sev = None
            action = "River stage within normal hydrological capacity. Continue continuous monitoring."

        return ThresholdEvaluationResult(
            gauge_id=norm,
            station_name=station,
            river_name=river,
            current_level_m=lvl,
            warning_level_m=warn_lvl,
            danger_level_m=danger_lvl,
            head_above_warning_m=max(0.0, head_warn),
            head_above_danger_m=max(0.0, head_danger),
            threshold_exceeded=exceeded,
            status=st,
            alert_severity=sev,
            action_recommended=action,
        )

    def record_observation(
        self,
        gauge_id: str,
        water_level_m: float,
        source: str = "MANUAL_TELEMETRY",
        timestamp_utc: Optional[str] = None,
    ) -> ThresholdEvaluationResult:
        """
        Record a live or simulated stage observation, update state and database,
        and evaluate threshold status.
        """
        norm = self._normalize_id(gauge_id)
        now = timestamp_utc or datetime.now(timezone.utc).isoformat()

        eval_res = self.evaluate_threshold(norm, simulated_level_m=water_level_m)

        with self._lock:
            if norm in self._gauges:
                prev_lvl = self._gauges[norm]["current_level_m"]
                delta = round(water_level_m - prev_lvl, 2)
                if delta > 0.15:
                    trend = RiverTrend.RISING
                elif delta < -0.15:
                    trend = RiverTrend.FALLING
                else:
                    trend = RiverTrend.STABLE

                self._gauges[norm].update({
                    "current_level_m": round(water_level_m, 2),
                    "status": eval_res.status,
                    "trend_24h": trend,
                    "delta_24h_m": delta,
                    "last_observation_utc": now,
                })

        # Persist observation in SQLite
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO river_gauge_records (
                        gauge_id, station_name, river_name, basin_name, latitude, longitude,
                        current_level_m, warning_level_m, danger_level_m, status, trend_24h, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        norm,
                        eval_res.station_name,
                        eval_res.river_name,
                        self._gauges[norm]["basin_name"],
                        self._gauges[norm]["latitude"],
                        self._gauges[norm]["longitude"],
                        round(water_level_m, 2),
                        eval_res.warning_level_m,
                        eval_res.danger_level_m,
                        eval_res.status.value,
                        self._gauges[norm]["trend_24h"].value,
                        now,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Failed to persist river gauge observation: %s", exc)

        logger.info(
            "Gauge %s (%s) observation: %.2fm | Status: %s",
            norm,
            eval_res.station_name,
            water_level_m,
            eval_res.status.value,
        )
        return eval_res

    def get_history(self, gauge_id: str, limit: int = 24) -> List[RiverGaugeHistoryPoint]:
        """
        Retrieve historical observation time series for a gauge.
        Returns persistent database rows, or generates realistic 24h trajectory.
        """
        norm = self._normalize_id(gauge_id)
        history = []

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT recorded_at, current_level_m, status
                    FROM river_gauge_records
                    WHERE gauge_id = ?
                    ORDER BY id DESC LIMIT ?;
                    """,
                    (norm, limit),
                )
                rows = cursor.fetchall()
                if rows:
                    prev_lvl = None
                    for r in reversed(rows):
                        ts, lvl, st = r[0], float(r[1]), r[2]
                        delta = round(lvl - prev_lvl, 2) if prev_lvl is not None else 0.0
                        prev_lvl = lvl
                        history.append(
                            RiverGaugeHistoryPoint(
                                timestamp_utc=ts,
                                water_level_m=lvl,
                                status=RiverGaugeStatus(st) if st in ("NORMAL", "WARNING", "DANGER") else RiverGaugeStatus.NORMAL,
                                delta_prev_m=delta,
                            )
                        )
                    return history
        except Exception as exc:
            logger.debug("History query failed: %s", exc)

        # Generate realistic fallback trajectory for gauge
        gauge = self.get_gauge(norm)
        if not gauge:
            return []

        base_lvl = gauge.current_level_m
        warn_lvl = gauge.warning_level_m
        now = datetime.now(timezone.utc)

        for i in range(limit - 1, -1, -1):
            t = now - timedelta(hours=i)
            # Gentle sinusoidal diurnal variance
            var = 0.4 * (1.0 - (i / max(1, limit)))
            sim_lvl = round(base_lvl - 0.3 * (i / limit) + var, 2)
            st = RiverGaugeStatus.DANGER if sim_lvl >= gauge.danger_level_m else (
                RiverGaugeStatus.WARNING if sim_lvl >= warn_lvl else RiverGaugeStatus.NORMAL
            )
            history.append(
                RiverGaugeHistoryPoint(
                    timestamp_utc=t.isoformat(),
                    water_level_m=sim_lvl,
                    status=st,
                    delta_prev_m=round(var, 2),
                )
            )

        return history


# Singleton accessor
_gauge_service: Optional[GaugeService] = None
_service_lock = threading.Lock()


def get_gauge_service() -> GaugeService:
    """Get or initialize singleton GaugeService."""
    global _gauge_service
    if _gauge_service is None:
        with _service_lock:
            if _gauge_service is None:
                _gauge_service = GaugeService()
    return _gauge_service
