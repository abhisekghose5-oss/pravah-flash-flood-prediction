"""
PRAVAH — Community Reporting & Crowdsourced Intelligence Test Suite
Tests:
1. Report Creation (Flood, Blocked Road, Water Level, General Incident)
2. Validation & Coordinate Guardrails
3. Photo Upload Security & Magic Byte Inspection
4. Moderation Workflow & Status Transitions
5. Spatial-Temporal Duplicate Clustering
6. Map GeoJSON & KPI Statistics
7. Privacy Protection (PII masking)
8. Ground-Truth Intelligence Pipeline Signals
"""

import io
import unittest
from fastapi.testclient import TestClient

from src.api.app import app
from src.community.models.incident import ReportStatus, ReportType, RoadStatus, SeverityLevel
from src.community.services.geolocation_service import find_nearest_gauge_station
from src.community.services.photo_service import verify_image_magic_bytes


class TestCommunityReporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Report Creation
    # -------------------------------------------------------------------------

    def test_create_valid_flood_observation(self):
        """Submit a valid flood observation report with water depth and severity."""
        payload = {
            "report_type": ReportType.FLOOD_OBSERVATION.value,
            "description": "Rising floodwaters have entered ground floor shops near the riverbank.",
            "severity": SeverityLevel.HIGH.value,
            "latitude": 18.0833,
            "longitude": 73.4167,
            "water_depth": 1.2,
            "location_name": "Mahad Riverside Bazaar",
            "district": "Raigad",
            "reporter_name": "Kishore Patil",
            "reporter_contact": "+919876543210",
        }
        res = self.client.post("/api/community/reports", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()

        self.assertIn("report_code", data)
        self.assertTrue(data["report_code"].startswith("CR-"))
        self.assertEqual(data["report_type"], ReportType.FLOOD_OBSERVATION.value)
        self.assertEqual(data["severity"], SeverityLevel.HIGH.value)
        self.assertEqual(data["water_depth"], 1.2)
        self.assertEqual(data["verification_status"], ReportStatus.PENDING_REVIEW.value)
        self.assertFalse(data["is_verified"])
        # Verify privacy: Reporter contact must NOT be leaked
        self.assertNotIn("reporter_contact", data)
        self.assertEqual(data["reporter_display"], "Kishore P.")

    def test_create_valid_blocked_road(self):
        """Submit a blocked road hazard report."""
        payload = {
            "report_type": ReportType.BLOCKED_ROAD.value,
            "description": "Landslide debris and 0.9m flash flood stream completely blocking highway.",
            "severity": SeverityLevel.CRITICAL.value,
            "latitude": 17.9237,
            "longitude": 73.8016,
            "road_status": RoadStatus.COMPLETELY_BLOCKED.value,
            "road_name": "SH-72 Mahabaleshwar Ghat",
            "hazard_cause": "Landslide & Torrential Runoff",
            "location_name": "Pasarni Ghat Mile 14",
            "district": "Satara",
        }
        res = self.client.post("/api/community/reports", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()

        self.assertEqual(data["road_status"], RoadStatus.COMPLETELY_BLOCKED.value)
        self.assertEqual(data["road_name"], "SH-72 Mahabaleshwar Ghat")
        self.assertEqual(data["hazard_cause"], "Landslide & Torrential Runoff")

    def test_create_valid_water_level_observation(self):
        """Submit a citizen water-level gauge observation."""
        payload = {
            "report_type": ReportType.WATER_LEVEL.value,
            "description": "Water mark at bridge marker reached 2.4 meters. River stage is swift.",
            "severity": SeverityLevel.MODERATE.value,
            "latitude": 26.1878,
            "longitude": 91.6916,
            "water_depth": 2.4,
            "location_name": "Guwahati Saraighat Bridge",
            "district": "Kamrup Metropolitan",
        }
        res = self.client.post("/api/community/reports", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["water_depth"], 2.4)
        self.assertEqual(data["state_region"], "Northeast")

    def test_create_valid_general_incident(self):
        """Submit a general flood incident (infrastructure scouring/erosion)."""
        payload = {
            "report_type": ReportType.GENERAL_INCIDENT.value,
            "description": "Embankment breach near culvert approach road. Water encroaching farmland.",
            "severity": SeverityLevel.HIGH.value,
            "latitude": 26.4983,
            "longitude": 90.9192,
            "hazard_cause": "Embankment Scour",
            "location_name": "Barpeta Beki Bund",
            "district": "Barpeta",
        }
        res = self.client.post("/api/community/reports", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["hazard_cause"], "Embankment Scour")

    def test_missing_required_fields_rejection(self):
        """Reject report with missing description or missing coordinates."""
        invalid_payload = {
            "report_type": "FLOOD_OBSERVATION",
            # missing description and latitude/longitude
        }
        res = self.client.post("/api/community/reports", json=invalid_payload)
        self.assertEqual(res.status_code, 422)

    def test_invalid_coordinates_rejection(self):
        """Reject out-of-bounds coordinates."""
        bad_lat = {
            "report_type": "FLOOD_OBSERVATION",
            "description": "Test invalid latitude",
            "latitude": 125.0,  # illegal > 90
            "longitude": 73.0,
        }
        res = self.client.post("/api/community/reports", json=bad_lat)
        self.assertEqual(res.status_code, 422)

        null_island = {
            "report_type": "FLOOD_OBSERVATION",
            "description": "Test null island coordinate",
            "latitude": 0.0,
            "longitude": 0.0,
        }
        res = self.client.post("/api/community/reports", json=null_island)
        self.assertEqual(res.status_code, 422)

    # -------------------------------------------------------------------------
    # 2. Photo Upload Security & Inspection
    # -------------------------------------------------------------------------

    def test_magic_bytes_detection(self):
        """Verify binary signature checker for authentic images."""
        jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        webp_header = b"RIFF\x24\x00\x00\x00WEBPVP8 "
        fake_header = b"MZ\x90\x00\x03\x00\x00\x00"  # Windows EXE

        self.assertTrue(verify_image_magic_bytes(jpeg_header, ".jpg"))
        self.assertTrue(verify_image_magic_bytes(png_header, ".png"))
        self.assertTrue(verify_image_magic_bytes(webp_header, ".webp"))
        self.assertFalse(verify_image_magic_bytes(fake_header, ".jpg"))

    def test_multipart_report_with_valid_photo(self):
        """Submit report with valid JPEG photo through multipart form endpoint."""
        fake_jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00" + b"\x00" * 200
        files = {
            "photo": ("flood_scene.jpg", io.BytesIO(fake_jpeg_content), "image/jpeg"),
        }
        data = {
            "report_type": "FLOOD_OBSERVATION",
            "description": "Severe overtopping near Chiplun bridge. Photo attached.",
            "severity": "HIGH",
            "latitude": "17.5323",
            "longitude": "73.5186",
            "location_name": "Chiplun Bridge",
            "district": "Ratnagiri",
        }
        res = self.client.post("/api/community/reports/multipart", data=data, files=files)
        self.assertEqual(res.status_code, 201)
        res_data = res.json()
        self.assertIsNotNone(res_data["photo_url"])
        self.assertTrue(res_data["photo_url"].startswith("/uploads/community_photos/"))
        self.assertTrue(res_data["photo_url"].endswith(".jpg"))

    def test_unsupported_file_extension_rejection(self):
        """Reject executable or text files disguised as photos."""
        bad_file = {
            "photo": ("malicious.exe", io.BytesIO(b"MZ executable header"), "application/octet-stream"),
        }
        data = {
            "report_type": "FLOOD_OBSERVATION",
            "description": "Attempting bad upload.",
            "latitude": "18.0",
            "longitude": "73.0",
        }
        res = self.client.post("/api/community/reports/multipart", data=data, files=bad_file)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported file format", res.json()["detail"])

    def test_attach_additional_photo_to_existing_report(self):
        """Attach a secondary photo to an existing report."""
        # Create a report first
        payload = {
            "report_type": "BLOCKED_ROAD",
            "description": "Karad bypass blocked by fallen trees.",
            "latitude": 17.2889,
            "longitude": 74.1844,
        }
        create_res = self.client.post("/api/community/reports", json=payload)
        rep_id = create_res.json()["id"]

        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100
        files = {
            "photo": ("trees.png", io.BytesIO(fake_png), "image/png"),
        }
        photo_res = self.client.post(f"/api/community/reports/{rep_id}/photos", files=files)
        self.assertEqual(photo_res.status_code, 200)
        data = photo_res.json()
        self.assertIsNotNone(data["photo_url"])

    # -------------------------------------------------------------------------
    # 3. Moderation & Lifecycle Transitions
    # -------------------------------------------------------------------------

    def test_moderation_lifecycle_flow(self):
        """Verify lifecycle transition: PENDING_REVIEW -> VERIFIED -> RESOLVED."""
        # 1. Create report
        payload = {
            "report_type": "FLOOD_OBSERVATION",
            "description": "Lonavala flooded railway subway observation.",
            "latitude": 18.7557,
            "longitude": 73.4091,
        }
        create_res = self.client.post("/api/community/reports", json=payload)
        rep_id = create_res.json()["id"]
        self.assertEqual(create_res.json()["verification_status"], "PENDING_REVIEW")

        # 2. Moderate to VERIFIED
        verify_res = self.client.patch(
            f"/api/community/reports/{rep_id}/status",
            json={"verification_status": "VERIFIED", "moderator_notes": "Ground verified by NDRF Unit 5"}
        )
        self.assertEqual(verify_res.status_code, 200)
        self.assertEqual(verify_res.json()["verification_status"], "VERIFIED")
        self.assertTrue(verify_res.json()["is_verified"])
        self.assertIn("NDRF Unit 5", verify_res.json()["moderator_notes"])

        # 3. Moderate to RESOLVED
        resolve_res = self.client.patch(
            f"/api/community/reports/{rep_id}/status",
            json={"verification_status": "RESOLVED", "moderator_notes": "Pumping completed, road clear."}
        )
        self.assertEqual(resolve_res.status_code, 200)
        self.assertEqual(resolve_res.json()["verification_status"], "RESOLVED")

    def test_prohibited_status_transition_rejection(self):
        """Verify illegal status transition is blocked with 400 Bad Request."""
        # Create report and reject it
        payload = {
            "report_type": "GENERAL_INCIDENT",
            "description": "False spam alert for testing moderation.",
            "latitude": 18.5204,
            "longitude": 73.8567,
        }
        create_res = self.client.post("/api/community/reports", json=payload)
        rep_id = create_res.json()["id"]

        self.client.patch(
            f"/api/community/reports/{rep_id}/status",
            json={"verification_status": "REJECTED"}
        )

        # Attempt illegal transition directly from REJECTED to RESOLVED
        illegal_res = self.client.patch(
            f"/api/community/reports/{rep_id}/status",
            json={"verification_status": "RESOLVED"}
        )
        self.assertEqual(illegal_res.status_code, 400)
        self.assertIn("Invalid lifecycle transition", illegal_res.json()["detail"])

    # -------------------------------------------------------------------------
    # 4. Duplicate Detection & Spatial Clustering
    # -------------------------------------------------------------------------

    def test_duplicate_spatial_clustering(self):
        """
        Verify that multiple citizen submissions within 1km and 2 hours for the
        same report type are clustered under the parent incident ID.
        """
        # Generate unique test location to prevent collision across test runs
        import time
        unique_offset = (time.time() % 1000) / 1000.0
        test_lat = 19.2000 + unique_offset
        test_lon = 73.1000 + unique_offset

        # Primary report
        primary_payload = {
            "report_type": "BLOCKED_ROAD",
            "description": f"Test road blockage event {time.time()}",
            "latitude": test_lat,
            "longitude": test_lon,
            "road_name": "Test Highway",
        }
        res1 = self.client.post("/api/community/reports", json=primary_payload)
        self.assertEqual(res1.status_code, 201)
        r1 = res1.json()
        primary_id = r1["id"]

        # Duplicate report ~100m away (0.001 deg ≈ 111m)
        dup_payload = {
            "report_type": "BLOCKED_ROAD",
            "description": f"Massive debris reported by citizen 2 at {time.time()}",
            "latitude": test_lat + 0.0008,
            "longitude": test_lon + 0.0008,
            "road_name": "Test Highway",
        }
        res2 = self.client.post("/api/community/reports", json=dup_payload)
        self.assertEqual(res2.status_code, 201)
        r2 = res2.json()

        # Check duplicate clustering associations
        self.assertTrue(r2["is_duplicate"])
        self.assertEqual(r2["parent_incident_id"], primary_id)

        # Check cluster query endpoint
        clusters_res = self.client.get("/api/community/clusters")
        self.assertEqual(clusters_res.status_code, 200)
        clusters = clusters_res.json()
        matched_cluster = next((c for c in clusters if c["cluster_id"] == primary_id), None)
        self.assertIsNotNone(matched_cluster)
        self.assertGreaterEqual(matched_cluster["child_count"], 2)

    # -------------------------------------------------------------------------
    # 5. Map GeoJSON & KPI Statistics
    # -------------------------------------------------------------------------

    def test_map_geojson_feature_collection(self):
        """Verify GET /api/community/reports/map returns standard GeoJSON."""
        res = self.client.get("/api/community/reports/map")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIsInstance(data["features"], list)
        self.assertGreaterEqual(len(data["features"]), 1)

        first_feature = data["features"][0]
        self.assertEqual(first_feature["type"], "Feature")
        self.assertIn("geometry", first_feature)
        self.assertEqual(first_feature["geometry"]["type"], "Point")
        self.assertEqual(len(first_feature["geometry"]["coordinates"]), 2)
        self.assertIn("properties", first_feature)
        self.assertIn("report_code", first_feature["properties"])

    def test_community_statistics_endpoint(self):
        """Verify GET /api/community/stats returns summary metrics for KPI cards."""
        res = self.client.get("/api/community/stats")
        self.assertEqual(res.status_code, 200)
        stats = res.json()

        self.assertIn("total_reports", stats)
        self.assertIn("reports_today", stats)
        self.assertIn("pending_verification", stats)
        self.assertIn("verified_reports", stats)
        self.assertIn("blocked_roads", stats)
        self.assertIn("active_incidents", stats)
        self.assertGreaterEqual(stats["total_reports"], 4)

    # -------------------------------------------------------------------------
    # 6. Geolocation Proximity & Intelligence Pipeline Signals
    # -------------------------------------------------------------------------

    def test_nearest_gauge_station_lookup(self):
        """Verify spatial lookup identifies the nearest PRAVAH gauge station."""
        # Coordinates near Mahad station (18.0833, 73.4167)
        stn = find_nearest_gauge_station(18.0900, 73.4200)
        self.assertIsNotNone(stn)
        self.assertEqual(stn["station_id"], "MH_GAK_17")
        self.assertEqual(stn["station_name"], "Mahad")
        self.assertLess(stn["distance_km"], 2.0)

    def test_ground_truth_intelligence_signals_endpoint(self):
        """Verify GET /api/community/signals computes ground signals without crashing."""
        res = self.client.get("/api/community/signals?radius_km=50&window_hours=24")
        self.assertEqual(res.status_code, 200)
        signals = res.json()

        self.assertIn("verified_reports_count", signals)
        self.assertIn("ground_truth_confidence", signals)
        self.assertIn("ground_truth_escalation_signal", signals)
        self.assertIn("summary", signals)


if __name__ == "__main__":
    unittest.main()
