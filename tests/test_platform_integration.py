"""
PRAVAH — Central Platform Integration & Consolidation Test Suite (SIH 2026).
Verifies:
1. Additive Database Migrations & Version Tracking
2. River Gauge Monitoring Module (CWC & Northeast Gauges, Threshold Checks, History)
3. IVRS Voice Calling Channel & TwiML Synthesis
4. Centralized Multi-Channel Alerting (SMS, WhatsApp, Telegram, IVRS)
5. Explainable AI Failure Isolation
6. Flood Simulation Inundation ➔ Safe Evacuation Routing
7. End-to-End Disaster Response Lifecycle (6 Stages)
8. Unified Health Diagnostics across all 9 Subsystems
9. 100% Backward Compatibility of Existing Endpoints
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.app import app
from src.data.db import get_connection
from src.data.migrations import get_migration_status
from src.gauges.gauge_service import get_gauge_service
from src.gauges.models.gauge import RiverGaugeStatus
from src.integration.platform_orchestrator import get_platform_orchestrator


class TestPlatformIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.orchestrator = get_platform_orchestrator()
        cls.gauge_service = get_gauge_service()

    # -------------------------------------------------------------------------
    # 1. Database Migrations & Schema Verification
    # -------------------------------------------------------------------------

    def test_database_migrations_applied_and_tracked(self):
        """Verify schema_migrations table tracks applied versions."""
        status = get_migration_status()
        self.assertGreaterEqual(status["applied_count"], 2)
        self.assertIn("001_initial_schema", status["applied_versions"])
        self.assertIn("002_integration_entities", status["applied_versions"])

        # Verify all additive tables exist in SQLite
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]

        required_tables = [
            "schema_migrations",
            "subscriptions",
            "sos_reports",
            "relief_shelters",
            "community_reports",
            "multi_channel_alerts",
            "alert_channel_deliveries",
            "evacuation_routes",
            "river_gauge_records",
            "ivrs_call_records",
            "xai_explanation_records",
            "digital_twin_simulation_records",
            "flood_propagation_simulation_records",
        ]
        for tbl in required_tables:
            self.assertIn(tbl, tables, f"Expected table '{tbl}' to exist in SQLite database")

    # -------------------------------------------------------------------------
    # 2. River Gauge Monitoring Module
    # -------------------------------------------------------------------------

    def test_river_gauge_catalog_listing(self):
        """Verify catalog returns CWC Maharashtra and Northeast gauges."""
        resp = self.client.get("/api/gauges")
        self.assertEqual(resp.status_code, 200)
        gauges = resp.json()
        self.assertGreaterEqual(len(gauges), 60)

        # Verify region filtering
        resp_mh = self.client.get("/api/gauges?region=Maharashtra")
        self.assertEqual(resp_mh.status_code, 200)
        self.assertEqual(len(resp_mh.json()), 20)

        resp_ne = self.client.get("/api/gauges?region=Northeast")
        self.assertEqual(resp_ne.status_code, 200)
        self.assertEqual(len(resp_ne.json()), 46)

    def test_river_gauge_telemetry_and_history(self):
        """Verify single gauge telemetry lookup and historical hydrograph series."""
        resp = self.client.get("/api/gauges/684")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["clean_id"], "684")
        self.assertEqual(data["station_name"], "Karad")
        self.assertEqual(data["river_name"], "Krishna")
        self.assertIn("current_level_m", data)
        self.assertIn("warning_level_m", data)
        self.assertIn("danger_level_m", data)

        # History
        hist_resp = self.client.get("/api/gauges/684/history?limit=12")
        self.assertEqual(hist_resp.status_code, 200)
        hist = hist_resp.json()
        self.assertGreater(len(hist), 0)
        self.assertIn("water_level_m", hist[0])

    def test_river_gauge_observation_post(self):
        """Verify posting a new hydrometric stage observation."""
        obs_payload = {
            "water_level_m": 565.00,
            "source": "MANUAL_TELEMETRY",
        }
        resp = self.client.post("/api/gauges/684/observe", json=obs_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["gauge_id"], "INDOFLOODS-gauge-684")
        self.assertEqual(data["current_level_m"], 565.00)
        self.assertTrue(data["threshold_exceeded"])
        self.assertIn(data["status"], ["WARNING", "DANGER"])

    # -------------------------------------------------------------------------
    # 3. IVRS Voice Calling Channel
    # -------------------------------------------------------------------------

    def test_ivrs_call_dispatch_and_status(self):
        """Verify IVRS outbound voice call queueing and status retrieval."""
        call_req = {
            "recipient_phone": "+919876543210",
            "message": "Urgent emergency notice from PRAVAH flood early warning network. Evacuate low-lying river areas.",
            "severity": "CRITICAL",
        }
        resp = self.client.post("/api/ivrs/call", json=call_req)
        self.assertEqual(resp.status_code, 200)
        call_data = resp.json()
        self.assertEqual(call_data["status"], "success")
        self.assertEqual(call_data["channel"], "ivrs")
        self.assertIn("call_id", call_data)

        # Check call status
        status_resp = self.client.get(f"/api/ivrs/status/{call_data['call_id']}")
        self.assertEqual(status_resp.status_code, 200)

        # Check calls list
        list_resp = self.client.get("/api/ivrs/calls?limit=5")
        self.assertEqual(list_resp.status_code, 200)
        calls = list_resp.json()
        self.assertGreater(len(calls), 0)

    # -------------------------------------------------------------------------
    # 4. Central Multi-Channel Alert Dispatch (Includes IVRS)
    # -------------------------------------------------------------------------

    def test_multi_channel_alert_dispatch_includes_ivrs(self):
        """Verify AlertManager dispatches concurrently to SMS, WhatsApp, Telegram, and IVRS."""
        trigger_payload = {
            "location": "Takli CWC Station",
            "region": "Maharashtra",
            "river_level": 425.0,
            "river_threshold": 419.0,
            "risk_score": 92.0,
            "alert_type": "RIVER_LEVEL",
            "severity": "EVACUATION",
            "channels": ["sms", "whatsapp", "telegram", "ivrs"],
            "custom_recipient_phone": "+919876543210",
        }
        resp = self.client.post("/api/alerts/trigger", json=trigger_payload)
        self.assertEqual(resp.status_code, 200)
        res = resp.json()
        self.assertIn("channels", res)
        chan_names = [c["channel"] for c in res["channels"]]
        self.assertIn("sms", chan_names)
        self.assertIn("whatsapp", chan_names)
        self.assertIn("telegram", chan_names)
        self.assertIn("ivrs", chan_names)

    # -------------------------------------------------------------------------
    # 5. Integration Workflow: River Gauge Threshold Breach
    # -------------------------------------------------------------------------

    def test_workflow_river_threshold_alert(self):
        """Verify gauge threshold check initiates multi-channel alert on danger."""
        # Normal stage: No alert
        norm_req = {
            "gauge_id": "684",
            "simulated_level_m": 500.0,
        }
        resp_norm = self.client.post("/api/integration/workflow/river-threshold-alert", json=norm_req)
        self.assertEqual(resp_norm.status_code, 200)
        self.assertFalse(resp_norm.json()["alert_triggered"])

        # Danger stage: Alert triggered (Karad danger mark is 567.04m)
        danger_req = {
            "gauge_id": "684",
            "simulated_level_m": 570.0,
            "channels": ["sms", "whatsapp", "ivrs"],
            "custom_recipient": "+919988776655",
        }
        resp_danger = self.client.post("/api/integration/workflow/river-threshold-alert", json=danger_req)
        self.assertEqual(resp_danger.status_code, 200)
        data = resp_danger.json()
        self.assertTrue(data["alert_triggered"])
        self.assertEqual(data["status"], "ALERT_TRIGGERED")
        self.assertIn("alert_dispatch", data)

    # -------------------------------------------------------------------------
    # 6. Integration Workflow: ML Predict + Explain (Failure Isolated)
    # -------------------------------------------------------------------------

    def test_workflow_predict_and_explain_success(self):
        """Verify ML prediction succeeds and attaches SHAP feature explanations."""
        req_payload = {
            "gauge_id": "684",
            "rainfall_history_10d": [10.0, 15.0, 20.0, 35.0, 50.0, 70.0, 95.0, 120.0, 150.0, 175.0],
            "onset_model": "RandomForest",
            "active_model": "XGBoost",
            "explain": True,
        }
        resp = self.client.post("/api/integration/workflow/predict-and-explain", json=req_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("prediction", data)
        self.assertIn("task_a_onset", data["prediction"])
        self.assertIn("xai_status", data)
        self.assertIn(data["xai_status"], ["SUCCESS", "UNAVAILABLE"])

    def test_workflow_predict_and_explain_failure_isolation(self):
        """Verify that if XAI fails, ML prediction still returns successfully."""
        with patch.object(self.orchestrator.xai_manager, "explain", side_effect=RuntimeError("SHAP Kernel OOM")):
            res = self.orchestrator.predict_and_explain(
                gauge_id="684",
                rainfall_history_10d=[5.0, 5.0, 10.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 80.0],
                explain=True,
            )
            self.assertIn("prediction", res)
            self.assertEqual(res["xai_status"], "UNAVAILABLE")
            self.assertIn("error", res["xai_explanation"])
            self.assertIn("SHAP Kernel OOM", res["xai_explanation"]["error"])

    # -------------------------------------------------------------------------
    # 7. Integration Workflow: Simulation to Evacuation
    # -------------------------------------------------------------------------

    def test_workflow_simulation_to_evacuation(self):
        """Verify flood propagation run generates hazard map and calculates safe evacuation route."""
        sim_req = {
            "origin_lat": 17.289,
            "origin_lng": 74.181,
            "preferred_objective": "LOWEST_RISK",
            "scenario_type": "rainfall",
            "simulation_period_hours": 6,
            "rainfall_mm": 140.0,
            "catchment_id": "684",
        }
        resp = self.client.post("/api/integration/workflow/simulation-to-evacuation", json=sim_req)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["workflow"], "simulation_to_evacuation")
        self.assertIn("simulation_id", data)
        self.assertIn("evacuation_plan", data)
        evac = data["evacuation_plan"]
        self.assertIn("primary_route", evac)
        self.assertGreater(evac["primary_route"]["distance_km"], 0.0)

    # -------------------------------------------------------------------------
    # 8. Integration Workflow: Full End-to-End Lifecycle
    # -------------------------------------------------------------------------

    def test_workflow_end_to_end_lifecycle(self):
        """Verify complete 6-stage lifecycle runs seamlessly."""
        e2e_req = {
            "gauge_id": "684",
            "rainfall_10d": [15.0, 20.0, 25.0, 40.0, 55.0, 80.0, 110.0, 135.0, 160.0, 180.0],
            "recipient_phone": "+919876543210",
            "channels": ["sms", "whatsapp", "telegram", "ivrs"],
        }
        resp = self.client.post("/api/integration/workflow/end-to-end", json=e2e_req)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertIn("stages", data)
        stages = data["stages"]
        self.assertIn("1_river_gauge", stages)
        self.assertIn("2_ml_prediction", stages)
        self.assertIn("3_explainable_ai", stages)
        self.assertIn("4_flood_simulation", stages)
        self.assertIn("5_evacuation_planning", stages)
        self.assertIn("6_alert_dispatch", stages)
        alert_chans = [c["channel"] for c in stages["6_alert_dispatch"]["channels"]]
        self.assertIn("ivrs", alert_chans)

    # -------------------------------------------------------------------------
    # 9. Unified Subsystems Health Diagnostic
    # -------------------------------------------------------------------------

    def test_unified_subsystems_health_diagnostic(self):
        """Verify /api/integration/health aggregates all 9 subsystems and database."""
        resp = self.client.get("/api/integration/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["overall_status"], "HEALTHY")
        subsystems = data["subsystems"]
        self.assertEqual(len(subsystems), 10)  # 9 subsystems + persistence database
        self.assertEqual(subsystems["river_gauge_monitoring"]["status"], "ONLINE")
        self.assertEqual(subsystems["sms_alert_channel"]["status"], "ONLINE")
        self.assertEqual(subsystems["whatsapp_alert_channel"]["status"], "ONLINE")
        self.assertEqual(subsystems["telegram_alert_channel"]["status"], "ONLINE")
        self.assertEqual(subsystems["ivrs_calling_channel"]["status"], "ONLINE")
        self.assertEqual(subsystems["evacuation_planning_engine"]["status"], "ONLINE")
        self.assertEqual(subsystems["explainable_ai_engine"]["status"], "ONLINE")
        self.assertEqual(subsystems["digital_twin_studio"]["status"], "ONLINE")
        self.assertEqual(subsystems["flood_propagation_simulator"]["status"], "ONLINE")
        self.assertEqual(subsystems["persistence_database"]["status"], "HEALTHY")

    # -------------------------------------------------------------------------
    # 10. Backward Compatibility Preservation
    # -------------------------------------------------------------------------

    def test_backward_compatibility_existing_endpoints(self):
        """Ensure baseline /api/health and /api/v1/predict/live are 100% preserved."""
        # 1. /api/health
        h_resp = self.client.get("/api/health")
        self.assertEqual(h_resp.status_code, 200)
        h_data = h_resp.json()
        self.assertEqual(h_data["status"], "System Online")
        self.assertTrue(h_data["model_loaded"])
        self.assertIn("available_models", h_data)
        self.assertEqual(h_data["total_catchments"], 20)

        # 2. /api/v1/predict/live
        p_resp = self.client.post(
            "/api/v1/predict/live",
            json={
                "gauge_id": "684",
                "rainfall_history_10d": [5.0, 10.0, 15.0, 20.0, 30.0, 45.0, 60.0, 80.0, 100.0, 120.0],
                "onset_model_name": "RandomForest",
                "active_model_name": "XGBoost",
            },
        )
        self.assertEqual(p_resp.status_code, 200)
        p_data = p_resp.json()
        self.assertIn("alert_tier", p_data)
        self.assertIn("task_a_onset", p_data)
        self.assertIn("task_b_active", p_data)


if __name__ == "__main__":
    unittest.main()
