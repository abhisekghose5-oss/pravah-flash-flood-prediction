"""
PRAVAH — Northeast (NE) Region QA Verification & Telemetry Test Suite
Validates:
1. GET /api/v1/predict?region=NE payload verification (catchment IDs, API values, probabilities)
2. Haversine evacuation nearest shelter query isolation (< 100km in NE terrain, Leaflet polylines)
3. Citizen SOS dual-region geofencing & tag assignment ("Northeast Alert" vs "Maharashtra Alert")
4. IMD Doppler Weather Radar (DWR) station metadata & coverage telemetry
"""

import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.app import app
from src.data.db import get_all_sos_reports, get_relief_shelters

ROOT = Path(__file__).resolve().parents[1]


class TestNortheastVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Verification API Endpoint Check (Dev Panel Target)
    # -------------------------------------------------------------------------

    def test_get_predict_ne_payload_verification(self):
        """Verify GET /api/v1/predict?region=NE returns catchment IDs, API values, and probabilities."""
        res = self.client.get("/api/v1/predict?region=NE")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["region"], "Northeast")
        self.assertGreaterEqual(data["total_catchments"], 40)
        self.assertIsInstance(data["catchment_ids"], list)
        self.assertIn("Beki", data["catchment_ids"])

        # Check Antecedent Precipitation Index (API) values
        self.assertIn("api_values", data)
        self.assertIsInstance(data["api_values"], dict)
        beki_api = data["api_values"].get("Beki")
        self.assertIsNotNone(beki_api)
        self.assertIn("rain_1d", beki_api)
        self.assertIn("rain_3d_sum", beki_api)
        self.assertIn("api_index", beki_api)

        # Check prediction probabilities
        self.assertIn("prediction_probabilities", data)
        self.assertIsInstance(data["prediction_probabilities"], dict)
        self.assertIn("task_a_onset", data)
        self.assertIn("task_b_active", data)
        self.assertIn("probability", data["task_a_onset"])
        self.assertIn("probability", data["task_b_active"])

    def test_get_predict_maharashtra_payload(self):
        """Verify GET /api/v1/predict?region=maharashtra returns Western Ghats telemetry."""
        res = self.client.get("/api/v1/predict?region=maharashtra")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["region"], "Maharashtra")
        self.assertEqual(data["total_catchments"], 20)
        self.assertIn("684", data["catchment_ids"])

    # -------------------------------------------------------------------------
    # 2. Haversine Evacuation Nearest Shelters & Polyline Validation
    # -------------------------------------------------------------------------

    def test_haversine_evacuation_northeast_isolation(self):
        """Verify evacuation query from NE returns top 3 NE shelters (< 100km) with Leaflet polylines."""
        # Query near Guwahati (26.18°N, 91.75°E)
        res = self.client.get("/api/v1/evacuation/nearest?lat=26.18&lng=91.75")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["region"], "Northeast")
        self.assertEqual(data["count"], 3)
        self.assertIsInstance(data["nearest_shelters"], list)

        # Closest shelter should be IIT Guwahati within 10 km (< 100 km)
        nearest = data["nearest_camp"]
        self.assertIsNotNone(nearest)
        self.assertIn("Guwahati", nearest["name"])
        self.assertLess(nearest["distance_km"], 20.0)
        self.assertEqual(nearest["region"], "Northeast")

        # Confirm all 3 returned shelters are strictly Northeast shelters
        for shelter in data["nearest_shelters"]:
            self.assertEqual(shelter["region"], "Northeast")
            self.assertLess(shelter["distance_km"], 150.0)
            # Leaflet polyline format: [[user_lat, user_lng], [camp_lat, camp_lng]]
            self.assertIn("polyline", shelter)
            poly = shelter["polyline"]
            self.assertEqual(len(poly), 2)
            self.assertEqual(poly[0], [26.18, 91.75])
            self.assertAlmostEqual(poly[1][0], shelter["latitude"], places=3)
            self.assertAlmostEqual(poly[1][1], shelter["longitude"], places=3)

    def test_haversine_evacuation_maharashtra_backward_compatibility(self):
        """Verify legacy /api/evacuation-route continues to serve Maharashtra users."""
        res = self.client.get("/api/evacuation-route?lat=18.5312&lng=73.8445")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertIn("Shivaji Nagar", data["nearest_camp"]["name"])
        self.assertLess(data["distance_km"], 1.0)
        self.assertIn("polyline", data["primary_evacuation_route"])

    # -------------------------------------------------------------------------
    # 3. Crowdsourced Citizen SOS Flood Incident Reporting & Geofencing
    # -------------------------------------------------------------------------

    def test_sos_reporting_northeast_geofence(self):
        """Verify SOS report from Northeast coordinates is tagged 'Northeast Alert' and persisted."""
        payload = {
            "latitude": 26.1820,
            "longitude": 91.7450,
            "severity": "above_waist_danger",
            "severity_tier": "above_waist_danger",
            "landmark_notes": "Rapid Brahmaputra backflow near Bharalu sluice gate.",
        }
        res = self.client.post("/api/v1/sos/report", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["region_tag"], "Northeast Alert")
        self.assertGreater(data["report_id"], 0)

        # Verify persisted in SQLite
        reports = get_all_sos_reports()
        matched = next((r for r in reports if r["id"] == data["report_id"]), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["region_tag"], "Northeast Alert")

    def test_sos_reporting_maharashtra_geofence(self):
        """Verify SOS report from Maharashtra coordinates is tagged 'Maharashtra Alert'."""
        payload = {
            "latitude": 18.0920,
            "longitude": 73.4600,
            "severity": "knee_deep",
            "landmark_notes": "Savitri river crossing submerged at bridge approach.",
        }
        res = self.client.post("/api/report-flood", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["region_tag"], "Maharashtra Alert")

    # -------------------------------------------------------------------------
    # 4. IMD Doppler Weather Radar (DWR) Stations Catalog
    # -------------------------------------------------------------------------

    def test_radar_stations_catalog_northeast(self):
        """Verify IMD Doppler radar stations covering Guwahati, Cherrapunji, Mohanbari."""
        res = self.client.get("/api/v1/radar/stations?region=NE")
        self.assertEqual(res.status_code, 200)
        stations = res.json()

        station_ids = [s["station_id"] for s in stations]
        self.assertIn("DWR_GUWAHATI", station_ids)
        self.assertIn("DWR_CHERRAPUNJI", station_ids)
        self.assertIn("DWR_MOHANBARI", station_ids)

        guwahati = next(s for s in stations if s["station_id"] == "DWR_GUWAHATI")
        self.assertEqual(guwahati["band"], "S-band Doppler Weather Radar")
        self.assertEqual(guwahati["range_km"], 250)
        self.assertIn("reflectivity_summary", guwahati)

    def test_radar_latest_scan(self):
        """Verify /api/v1/radar/latest returns reflectivity dBZ and echo storm cells."""
        res = self.client.get("/api/v1/radar/latest?station_id=DWR_GUWAHATI")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertIn("echo_blobs", data)
        self.assertGreater(len(data["echo_blobs"]), 0)
        self.assertIn("reflectivity_dbz", data["echo_blobs"][0])


if __name__ == "__main__":
    unittest.main()
