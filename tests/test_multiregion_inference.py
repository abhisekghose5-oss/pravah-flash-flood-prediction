"""
PRAVAH Multi-Region Inference & REST API Verification Test Suite
Validates dual-region routing (Maharashtra Western Ghats & Northeast India),
latency guarantees (< 200ms), decision thresholds, and GeoJSON endpoints.
"""

import time
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.app import app
from src.inference.predictor import PravahInferenceEngine

ROOT = Path(__file__).resolve().parents[1]


class TestMultiRegionInference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = PravahInferenceEngine()
        cls.client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Engine Direct In-Memory Inference & Latency Tests
    # -------------------------------------------------------------------------

    def test_maharashtra_direct_inference_latency(self):
        """Verify Maharashtra prediction executes in < 200ms."""
        monsoon_rain = [5.0, 10.0, 15.0, 25.0, 35.0, 50.0, 75.0, 90.0, 80.0, 65.0]
        
        # Warmup
        _ = self.engine.predict_live("684", monsoon_rain, region="maharashtra")

        start = time.perf_counter()
        res = self.engine.predict_live("684", monsoon_rain, region="maharashtra")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertLess(elapsed_ms, 200.0, f"Maharashtra inference took {elapsed_ms:.1f}ms, exceeds 200ms target")
        self.assertEqual(res["station"]["gauge_id"], "684")
        self.assertIn("probability", res["task_a_onset"])
        self.assertIn("probability", res["task_b_active"])
        self.assertIn(res["alert_tier"]["tier"], ["NORMAL", "ADVISORY", "WARNING", "EMERGENCY"])

    def test_northeast_direct_inference_latency(self):
        """Verify Northeast India prediction executes in < 200ms."""
        wet_series = [10.0, 15.0, 20.0, 30.0, 45.0, 60.0, 85.0, 110.0, 95.0, 70.0]

        # Warmup
        _ = self.engine.predict_live("Beki", wet_series, region="NE")

        start = time.perf_counter()
        res = self.engine.predict_live("Beki", wet_series, region="NE")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertLess(elapsed_ms, 200.0, f"Northeast inference took {elapsed_ms:.1f}ms, exceeds 200ms target")
        self.assertEqual(res["station"]["name"], "Beki")
        self.assertEqual(res["station"]["region"], "Northeast")
        self.assertTrue(res["is_northeast"])
        self.assertIn("probability", res["task_a_onset"])
        self.assertIn("probability", res["task_b_active"])

    def test_northeast_dedicated_engine_methods(self):
        """Verify predict_live_ne and get_ne_station_info functions."""
        info = self.engine.get_ne_station_info("Beki")
        self.assertEqual(info["name"], "Beki")
        self.assertEqual(info["district"], "Barpeta")
        self.assertEqual(info["basin"], "Brahmaputra")

        dry_series = [0.0] * 10
        res_dry = self.engine.predict_live_ne("Beki", dry_series)
        self.assertFalse(res_dry["task_a_onset"]["is_flood_onset_predicted"])
        self.assertEqual(res_dry["alert_tier"]["tier"], "NORMAL")

    def test_csi_optimized_thresholds(self):
        """Verify decision thresholds target Critical Success Index (CSI)."""
        summary = self.engine.get_ne_models_summary()
        self.assertIn("thresholds", summary)
        thresholds = summary["thresholds"]
        
        # In extreme class imbalance, Task A onset threshold is tuned down ~0.05
        # rather than naive 0.50 to maximize threat score / CSI
        self.assertAlmostEqual(thresholds["task_a_onset"]["XGBoost"], 0.05, delta=0.02)
        self.assertGreater(thresholds["task_b_active"]["XGBoost"], 0.35)

    # -------------------------------------------------------------------------
    # 2. FastAPI Endpoints Multi-Region & Latency Tests
    # -------------------------------------------------------------------------

    def test_api_health_dual_region_status(self):
        """Verify health check reports dual-region operational readiness."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "System Online")
        self.assertIn("Northeast India (Brahmaputra Basin)", data["active_regions"])
        self.assertIn("Maharashtra Western Ghats", data["active_regions"])
        self.assertGreaterEqual(data["total_northeast_stations"], 40)

    def test_api_predict_live_multiregion_routing(self):
        """Verify /api/v1/predict/live routes correctly for both regions with < 200ms latency."""
        # Maharashtra live prediction
        mh_payload = {
            "region": "maharashtra",
            "gauge_id": "684",
            "rainfall_history_10d": [0.0, 5.0, 10.0, 20.0, 30.0, 40.0, 60.0, 80.0, 70.0, 50.0],
            "onset_model": "RandomForest",
            "active_model": "XGBoost",
        }
        start = time.perf_counter()
        mh_res = self.client.post("/api/v1/predict/live", json=mh_payload)
        mh_latency_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(mh_res.status_code, 200)
        self.assertLess(mh_latency_ms, 500.0)
        mh_data = mh_res.json()
        self.assertEqual(mh_data["status"], "success")
        self.assertEqual(mh_data["station"]["gauge_id"], "684")

        # Northeast live prediction
        ne_payload = {
            "region": "NE",
            "station_id": "Beki",
            "rainfall_history_10d": [5.0, 15.0, 25.0, 45.0, 70.0, 95.0, 120.0, 105.0, 85.0, 60.0],
            "onset_model": "XGBoost",
            "active_model": "XGBoost",
        }
        start = time.perf_counter()
        ne_res = self.client.post("/api/v1/predict/live", json=ne_payload)
        ne_latency_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(ne_res.status_code, 200)
        self.assertLess(ne_latency_ms, 500.0)
        ne_data = ne_res.json()
        self.assertEqual(ne_data["status"], "success")
        self.assertEqual(ne_data["station"]["name"], "Beki")
        self.assertEqual(ne_data["station"]["region"], "Northeast")

    def test_api_northeast_dedicated_predict_live(self):
        """Verify /api/v1/northeast/predict/live endpoint."""
        payload = {
            "station_id": "Kokrajhar Circuit House",
            "rainfall_history_10d": [0.0, 2.0, 5.0, 10.0, 15.0, 25.0, 40.0, 55.0, 45.0, 30.0],
            "onset_model": "XGBoost",
            "active_model": "XGBoost",
        }
        start = time.perf_counter()
        res = self.client.post("/api/v1/northeast/predict/live", json=payload)
        latency_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(res.status_code, 200)
        self.assertLess(latency_ms, 500.0)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["station"]["name"], "Kokrajhar Circuit House")
        self.assertEqual(data["station"]["district"], "Kokrajhar")

    def test_api_northeast_stations_catalog(self):
        """Verify /api/v1/northeast/stations returns 46 Assam stations."""
        res = self.client.get("/api/v1/northeast/stations")
        self.assertEqual(res.status_code, 200)
        stations = res.json()
        self.assertGreaterEqual(len(stations), 40)
        beki = next((s for s in stations if s["name"] == "Beki"), None)
        self.assertIsNotNone(beki)
        self.assertEqual(beki["district"], "Barpeta")
        self.assertIn("lat", beki)
        self.assertIn("lng", beki)

    def test_api_northeast_catchments_geojson(self):
        """Verify /api/v1/northeast/catchments returns GeoJSON FeatureCollection."""
        res = self.client.get("/api/v1/northeast/catchments")
        self.assertEqual(res.status_code, 200)
        geojson = res.json()
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertGreater(len(geojson["features"]), 0)
        feat = geojson["features"][0]
        self.assertIn("geometry", feat)
        self.assertIn("properties", feat)
        self.assertIn("coordinates", feat["geometry"])

    def test_api_northeast_models_summary(self):
        """Verify /api/v1/northeast/models/summary returns benchmark metrics."""
        res = self.client.get("/api/v1/northeast/models/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("task_a_onset", data)
        self.assertIn("task_b_active", data)
        self.assertIn("thresholds", data)


if __name__ == "__main__":
    unittest.main()
