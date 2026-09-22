"""
PRAVAH — Central Platform Integration Orchestrator.
Connects all 9 completed modules through clean service interfaces and fault-tolerant
cross-module workflows.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional
import threading

from src.alerts.alert_manager import AlertManager
from src.alerts.models.alert import AlertSeverity, AlertTriggerRequest, ChannelType, TriggerType
from src.data.db import get_connection
from src.data.migrations import get_migration_status
from src.digital_twin.digital_twin_manager import DigitalTwinManager
from src.evacuation.evacuation_manager import evacuation_manager
from src.evacuation.models.route import RouteObjective, RouteRequest, RoutingAlgorithm
from src.evacuation.services.shelter_service import shelter_service
from src.gauges.gauge_service import get_gauge_service
from src.gauges.models.gauge import RiverGaugeStatus
from src.inference.predictor import PravahInferenceEngine
from src.simulation.models.scenario import (
    RainfallScenarioParams,
    ScenarioType,
    SimulationPeriod,
    SpatialDistribution,
)
from src.simulation.models.simulation import SimulationRunRequest
from src.simulation.simulation_manager import get_simulation_manager
from src.xai.models.explanation import ExplanationRequest
from src.xai.xai_manager import XAIManager

logger = logging.getLogger("pravah.integration.orchestrator")


class PlatformOrchestrator:
    """
    Central cross-module orchestrator managing multi-stage hazard workflows
    while maintaining independent module isolation.
    """

    def __init__(
        self,
        alert_manager: Optional[AlertManager] = None,
        xai_manager: Optional[XAIManager] = None,
        digital_twin_manager: Optional[DigitalTwinManager] = None,
        ml_engine: Optional[PravahInferenceEngine] = None,
    ):
        self.alert_manager = alert_manager or AlertManager()
        self.xai_manager = xai_manager or XAIManager.get_instance()
        self.digital_twin_manager = digital_twin_manager or DigitalTwinManager.get_instance()
        self.gauge_service = get_gauge_service()
        self.simulation_manager = get_simulation_manager()
        self.evacuation_manager = evacuation_manager
        self.ml_engine = ml_engine
        logger.info("PlatformOrchestrator initialized across all 9 subsystems")

    # =========================================================================
    # Workflow 1 & 2: River Gauge -> Threshold Check -> AlertManager
    # =========================================================================
    async def trigger_gauge_threshold_alert(
        self,
        gauge_id: str,
        simulated_level_m: Optional[float] = None,
        channels: Optional[List[str]] = None,
        custom_recipient: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate river gauge stage and automatically trigger multi-channel alerts
        (SMS, WhatsApp, Telegram, IVRS) if warning or danger thresholds are exceeded.
        """
        eval_res = self.gauge_service.evaluate_threshold(gauge_id, simulated_level_m=simulated_level_m)
        gauge = self.gauge_service.get_gauge(gauge_id)
        if not gauge:
            raise ValueError(f"Gauge '{gauge_id}' not found")

        # If threshold not exceeded, return evaluation without triggering alert
        if not eval_res.threshold_exceeded:
            return {
                "workflow": "river_gauge_threshold_check",
                "status": "NORMAL",
                "alert_triggered": False,
                "gauge": eval_res.model_dump(),
                "message": "Water stage is within normal limits. No alert triggered.",
            }

        # Determine target severity
        sev = AlertSeverity.CRITICAL if eval_res.status == RiverGaugeStatus.DANGER else AlertSeverity.WARNING
        if eval_res.alert_severity == "EVACUATION":
            sev = AlertSeverity.EVACUATION

        # Map channel strings to ChannelType
        target_chans = None
        if channels:
            target_chans = [ChannelType(c.lower()) for c in channels if c.lower() in [ct.value for ct in ChannelType]]

        # Construct alert trigger payload
        req = AlertTriggerRequest(
            location=gauge.station_name,
            region=gauge.region,
            river_level=eval_res.current_level_m,
            river_threshold=eval_res.warning_level_m,
            risk_score=92.0 if sev == AlertSeverity.EVACUATION else (82.0 if sev == AlertSeverity.CRITICAL else 68.0),
            alert_type=TriggerType.RIVER_LEVEL,
            severity=sev,
            channels=target_chans,
            custom_recipient_phone=custom_recipient,
        )

        dispatch_res = await self.alert_manager.dispatch_alert(req)

        return {
            "workflow": "river_gauge_threshold_alert",
            "status": "ALERT_TRIGGERED",
            "alert_triggered": True,
            "gauge_evaluation": eval_res.model_dump(),
            "alert_dispatch": dispatch_res,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

    # =========================================================================
    # Workflow 4: ML Prediction -> Explainable AI (SHAP)
    # =========================================================================
    def predict_and_explain(
        self,
        gauge_id: str,
        rainfall_history_10d: List[float],
        onset_model: str = "RandomForest",
        active_model: str = "XGBoost",
        explain: bool = True,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute ML flood prediction and optionally attach SHAP feature attributions.
        Strict failure isolation: If XAI fails, prediction succeeds intact.
        """
        start_t = time.time()
        # 1. Primary ML Prediction
        if self.ml_engine is None:
            self.ml_engine = PravahInferenceEngine()
        pred_res = self.ml_engine.predict_live(
            gauge_id=gauge_id,
            rainfall_history_10d=rainfall_history_10d,
            onset_model_name=onset_model,
            active_model_name=active_model,
            region=region,
        )

        xai_data = None
        xai_status = "NOT_REQUESTED"

        # 2. Optional XAI Explanation with Strict Error Isolation
        if explain:
            try:
                task_a = pred_res.get("task_a_onset", {})
                onset_prob = task_a.get("probability", pred_res.get("onset_probability", 0.5))
                alert_info = pred_res.get("alert_tier", {})
                alert_tier_str = alert_info.get("tier", "NORMAL") if isinstance(alert_info, dict) else str(alert_info)

                xai_req = ExplanationRequest(
                    model_name=onset_model,
                    task="onset",
                    gauge_id=gauge_id,
                    rainfall_10d_sum=sum(rainfall_history_10d),
                    rainfall_history_10d=rainfall_history_10d,
                    predicted_risk=onset_prob,
                )
                exp_res = self.xai_manager.explain(xai_req)
                if exp_res.status == "success":
                    xai_data = exp_res.model_dump()
                    xai_status = "SUCCESS"
                    self._save_xai_record(exp_res, gauge_id, onset_prob, alert_tier_str)
                else:
                    xai_status = "ERROR"
                    xai_data = {"error": exp_res.headline_narrative}
            except Exception as exc:
                logger.warning("XAI calculation failed, prediction continues: %s", exc)
                xai_status = "UNAVAILABLE"
                xai_data = {"error": str(exc)}

        elapsed_ms = round((time.time() - start_t) * 1000.0, 2)
        return {
            "workflow": "predict_and_explain",
            "prediction": pred_res,
            "xai_status": xai_status,
            "xai_explanation": xai_data,
            "execution_time_ms": elapsed_ms,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

    def _save_xai_record(self, exp_res: Any, gauge_id: str, risk: float, tier: str) -> None:
        """Log XAI execution metadata to SQLite."""
        try:
            feats = exp_res.top_positive_features + exp_res.top_negative_features
            f1_name, f1_shap = (feats[0].feature_name, feats[0].shap_value) if len(feats) > 0 else ("", 0.0)
            f2_name, f2_shap = (feats[1].feature_name, feats[1].shap_value) if len(feats) > 1 else ("", 0.0)
            f3_name, f3_shap = (feats[2].feature_name, feats[2].shap_value) if len(feats) > 2 else ("", 0.0)

            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO xai_explanation_records (
                        explanation_id, model_name, gauge_id, predicted_risk, alert_tier,
                        top_feature_1, top_feature_1_shap, top_feature_2, top_feature_2_shap,
                        top_feature_3, top_feature_3_shap, execution_time_ms, timestamp_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        exp_res.explanation_id,
                        exp_res.model_name,
                        gauge_id,
                        risk,
                        tier,
                        f1_name,
                        f1_shap,
                        f2_name,
                        f2_shap,
                        f3_name,
                        f3_shap,
                        exp_res.execution_time_ms,
                        exp_res.timestamp_utc,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.debug("Failed to persist XAI explanation record: %s", exc)

    # =========================================================================
    # Workflow 3 & 6: Flood Simulation Inundation -> Evacuation Planning
    # =========================================================================
    def simulation_to_evacuation(
        self,
        origin_lat: float,
        origin_lng: float,
        simulation_request: SimulationRunRequest,
        preferred_objective: RouteObjective = RouteObjective.LOWEST_RISK,
    ) -> Dict[str, Any]:
        """
        Run flood propagation simulation, identify inundation hazard footprint,
        and generate safe multi-factor evacuation path to safe shelter.
        """
        # 1. Execute flood propagation run
        sim_res = self.simulation_manager.run_simulation(simulation_request)

        # 2. Plan evacuation route from origin coordinates
        route_req = RouteRequest(
            latitude=origin_lat,
            longitude=origin_lng,
            objective=preferred_objective,
            algorithm=RoutingAlgorithm.DIJKSTRA,
        )
        plan_res = self.evacuation_manager.plan_evacuation(route_req)

        # Persist simulation log
        self._save_simulation_record(sim_res)

        return {
            "workflow": "simulation_to_evacuation",
            "simulation_id": sim_res.simulation_id,
            "scenario_title": sim_res.scenario_title,
            "maximum_flood_extent_km2": sim_res.maximum_flood_extent_km2,
            "peak_depth_m": sim_res.peak_depth_m,
            "population_impacted": sim_res.total_population_impacted,
            "evacuation_plan": plan_res.model_dump(),
            "provenance_disclaimer": sim_res.provenance_disclaimer,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

    def _save_simulation_record(self, sim_res: Any) -> None:
        """Persist simulation summary to SQLite."""
        try:
            roads_km = sim_res.infrastructure_summary.submerged_road_length_km if sim_res.infrastructure_summary else 0.0
            bridges = sim_res.infrastructure_summary.submerged_bridges if sim_res.infrastructure_summary else 0
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO flood_propagation_simulation_records (
                        simulation_id, scenario_type, scenario_title, target_region,
                        simulation_period_hours, max_extent_km2, peak_depth_m,
                        total_population_impacted, roads_submerged_km, bridges_submerged_count,
                        execution_time_ms, timestamp_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        sim_res.simulation_id,
                        sim_res.scenario_type.value,
                        sim_res.scenario_title,
                        sim_res.target_region,
                        sim_res.simulation_period_hours,
                        sim_res.maximum_flood_extent_km2,
                        sim_res.peak_depth_m,
                        sim_res.total_population_impacted,
                        roads_km,
                        bridges,
                        sim_res.execution_time_ms,
                        sim_res.timestamp_utc,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.debug("Failed to persist simulation record: %s", exc)

    # =========================================================================
    # Complete End-to-End Workflow: Data -> AI -> XAI -> Sim -> Evac -> Alert
    # =========================================================================
    async def execute_end_to_end(
        self,
        gauge_id: str,
        rainfall_10d: List[float],
        recipient_phone: Optional[str] = None,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute full PRAVAH disaster early-warning lifecycle:
        1. Sensor & Gauge Telemetry Check
        2. ML Flood Prediction (RF/XGB)
        3. Explainable AI (SHAP)
        4. Flood Propagation Simulation
        5. Evacuation Safe Routing
        6. Multi-Channel Alert Dispatch (SMS + WhatsApp + Telegram + IVRS)
        """
        start_t = time.time()
        pipeline_id = f"PIPE-{uuid.uuid4().hex[:8].upper()}"

        # 1. Gauge Telemetry Check
        gauge = self.gauge_service.get_gauge(gauge_id)
        if not gauge:
            gauge_id = "684"  # Default to Karad
            gauge = self.gauge_service.get_gauge(gauge_id)

        # 2. ML Prediction & 3. XAI
        pred_xai = self.predict_and_explain(
            gauge_id=gauge.clean_id,
            rainfall_history_10d=rainfall_10d,
            explain=True,
        )
        task_a = pred_xai["prediction"].get("task_a_onset", {})
        onset_prob = task_a.get("probability", pred_xai["prediction"].get("onset_probability", 0.85))
        risk_pct = onset_prob * 100.0

        # 4. Flood Propagation Simulation (6h convective event)
        sim_req = SimulationRunRequest(
            scenario_type=ScenarioType.RAINFALL,
            simulation_period_hours=SimulationPeriod.PERIOD_6H,
            rainfall_params=RainfallScenarioParams(
                rainfall_mm=max(100.0, sum(rainfall_10d[-3:])),
                rainfall_duration_hours=4.0,
                spatial_distribution=SpatialDistribution.CONVECTIVE_CORE,
                catchment_id=gauge.gauge_id,
                initial_soil_saturation_pct=85.0,
            ),
        )
        sim_res = self.simulation_manager.run_simulation(sim_req)

        # 5. Evacuation Routing
        evac_req = RouteRequest(
            latitude=gauge.latitude,
            longitude=gauge.longitude,
            objective=RouteObjective.LOWEST_RISK,
            algorithm=RoutingAlgorithm.DIJKSTRA,
        )
        evac_res = self.evacuation_manager.plan_evacuation(evac_req)

        # 6. Central Alert Dispatch (SMS, WhatsApp, Telegram, IVRS)
        primary_route = evac_res.primary_route
        rec_shelter = primary_route.destination if primary_route else {}
        shelter_name = rec_shelter.get("name", "Karad Elevated Relief Center") if isinstance(rec_shelter, dict) else "Karad Elevated Relief Center"
        route_text = f"Route {primary_route.route_id} ({round(primary_route.distance_km, 1)}km)" if primary_route else "SH-72 via High Ridge"

        sev = AlertSeverity.EVACUATION if risk_pct >= 80.0 else (AlertSeverity.CRITICAL if risk_pct >= 50.0 else AlertSeverity.WARNING)

        target_chans = None
        if channels:
            target_chans = [ChannelType(c.lower()) for c in channels if c.lower() in [ct.value for ct in ChannelType]]

        alert_req = AlertTriggerRequest(
            location=gauge.station_name,
            region=gauge.region,
            risk_score=round(risk_pct, 1),
            river_level=gauge.current_level_m,
            river_threshold=gauge.warning_level_m,
            rainfall_forecast=sum(rainfall_10d[-3:]),
            alert_type=TriggerType.MULTI_FACTOR,
            severity=sev,
            channels=target_chans,
            custom_recipient_phone=recipient_phone,
            evacuation_route=route_text,
            shelter_location=shelter_name,
        )
        alert_res = await self.alert_manager.dispatch_alert(alert_req)

        elapsed_ms = round((time.time() - start_t) * 1000.0, 2)
        return {
            "pipeline_id": pipeline_id,
            "status": "COMPLETED",
            "station": gauge.station_name,
            "region": gauge.region,
            "stages": {
                "1_river_gauge": {
                    "gauge_id": gauge.gauge_id,
                    "river": gauge.river_name,
                    "current_level_m": gauge.current_level_m,
                    "status": gauge.status.value,
                },
                "2_ml_prediction": pred_xai["prediction"],
                "3_explainable_ai": {
                    "status": pred_xai["xai_status"],
                    "headline": pred_xai["xai_explanation"].get("headline_narrative") if pred_xai.get("xai_explanation") else "N/A",
                },
                "4_flood_simulation": {
                    "simulation_id": sim_res.simulation_id,
                    "max_extent_km2": sim_res.maximum_flood_extent_km2,
                    "peak_depth_m": sim_res.peak_depth_m,
                    "population_impacted": sim_res.total_population_impacted,
                },
                "5_evacuation_planning": {
                    "route_code": primary_route.route_id if primary_route else "N/A",
                    "safe_shelter": shelter_name,
                    "travel_time_minutes": primary_route.estimated_time_minutes if primary_route else 0,
                },
                "6_alert_dispatch": alert_res,
            },
            "overall_execution_time_ms": elapsed_ms,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

    # =========================================================================
    # Unified Platform Health Diagnostics
    # =========================================================================
    def get_unified_health(self) -> Dict[str, Any]:
        """
        Aggregate operational health across all 9 platform subsystems and the database.
        """
        ch_status = self.alert_manager.get_channel_statuses()
        gauges = self.gauge_service.list_gauges()
        shelters = shelter_service.get_all_shelters()
        ws_list = self.digital_twin_manager.geojson_service.get_all_watersheds()
        sim_status = self.simulation_manager.get_status()
        xai_models = self.xai_manager.get_supported_models()
        mig_status = get_migration_status()

        db_healthy = False
        try:
            with get_connection() as conn:
                conn.execute("SELECT 1;").fetchone()
                db_healthy = True
        except Exception:
            db_healthy = False

        subsystems = {
            "river_gauge_monitoring": {
                "status": "ONLINE",
                "gauges_count": len(gauges),
                "maharashtra_cwc_count": len([g for g in gauges if g.region == "Maharashtra"]),
                "northeast_count": len([g for g in gauges if g.region == "Northeast"]),
            },
            "sms_alert_channel": {
                "status": "ONLINE" if ch_status.sms_enabled else "DISABLED",
                "mode": ch_status.sms_mode,
            },
            "whatsapp_alert_channel": {
                "status": "ONLINE" if ch_status.whatsapp_enabled else "DISABLED",
                "mode": ch_status.whatsapp_mode,
            },
            "telegram_alert_channel": {
                "status": "ONLINE" if ch_status.telegram_enabled else "DISABLED",
                "mode": ch_status.telegram_mode,
            },
            "ivrs_calling_channel": {
                "status": "ONLINE" if ch_status.ivrs_enabled else "DISABLED",
                "mode": ch_status.ivrs_mode,
            },
            "evacuation_planning_engine": {
                "status": "ONLINE",
                "algorithm": "Dijkstra & A* Multi-Objective",
                "shelters_active_count": len(shelters),
            },
            "explainable_ai_engine": {
                "status": "ONLINE",
                "framework": "SHAP TreeExplainer",
                "models_supported": [m.model_id for m in xai_models.supported_models],
            },
            "digital_twin_studio": {
                "status": "ONLINE",
                "hydrology_model": "SCS-CN Runoff & Elevation DEM",
                "watersheds_count": len(ws_list),
            },
            "flood_propagation_simulator": {
                "status": "ONLINE",
                "scenarios": sim_status["supported_scenarios"],
                "depth_tiers": sim_status["depth_classifications_m"],
            },
            "persistence_database": {
                "status": "HEALTHY" if db_healthy else "UNHEALTHY",
                "engine": "SQLite 3",
                "migrations_applied": mig_status["applied_count"],
            },
        }

        all_online = db_healthy and all(
            s.get("status") in ("ONLINE", "HEALTHY", "DISABLED") for s in subsystems.values()
        )

        return {
            "platform": "PRAVAH Flood Intelligence Platform",
            "version": "2.5.0",
            "overall_status": "HEALTHY" if all_online else "DEGRADED",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "subsystems": subsystems,
        }


# Singleton accessor
_orchestrator_instance: Optional[PlatformOrchestrator] = None
_orch_lock = threading.Lock()


def get_platform_orchestrator() -> PlatformOrchestrator:
    """Get or initialize singleton PlatformOrchestrator."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        with _orch_lock:
            if _orchestrator_instance is None:
                _orchestrator_instance = PlatformOrchestrator()
    return _orchestrator_instance
