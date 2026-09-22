from __future__ import annotations

import json
import unittest
from pathlib import Path
import pandas as pd
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


class PravahNewDatasetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.api.app import app
        cls.client = TestClient(app)

    def test_raw_datasets_exist_and_populated(self):
        expected_raw_files = [
            RAW_DIR / "soil" / "soil_hydrology_profiles.csv",
            RAW_DIR / "river_levels" / "cwc_daily_river_stages.csv",
            RAW_DIR / "dams" / "dams_reservoirs_master.csv",
            RAW_DIR / "terrain" / "catchment_terrain_orography.csv",
            RAW_DIR / "terrain" / "mountain_peaks_passes.csv",
            RAW_DIR / "safe_zones" / "safe_zones_registry.csv",
            RAW_DIR / "drainage" / "river_confluences_master.csv",
            RAW_DIR / "disaster_response" / "emergency_response_units.csv",
        ]
        for path in expected_raw_files:
            self.assertTrue(path.exists(), f"Missing raw dataset: {path}")
            df = pd.read_csv(path)
            self.assertGreater(len(df), 0, f"Raw dataset is empty: {path}")

    def test_processed_artifacts_validity(self):
        expected_processed = [
            PROCESSED_DIR / "soil_hydrology_features.csv",
            PROCESSED_DIR / "river_level_telemetry.csv",
            PROCESSED_DIR / "dams_reservoirs.csv",
            PROCESSED_DIR / "dams_reservoirs.geojson",
            PROCESSED_DIR / "mountain_terrain_features.csv",
            PROCESSED_DIR / "mountain_peaks_passes.geojson",
            PROCESSED_DIR / "safe_zones.csv",
            PROCESSED_DIR / "safe_zones.geojson",
            PROCESSED_DIR / "drainage_confluences.geojson",
            PROCESSED_DIR / "disaster_response_units.csv",
        ]
        for path in expected_processed:
            self.assertTrue(path.exists(), f"Missing processed artifact: {path}")

        # Check GeoJSONs have valid FeatureCollection structure
        for geojson_path in [
            PROCESSED_DIR / "dams_reservoirs.geojson",
            PROCESSED_DIR / "mountain_peaks_passes.geojson",
            PROCESSED_DIR / "safe_zones.geojson",
            PROCESSED_DIR / "drainage_confluences.geojson",
        ]:
            with open(geojson_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("type"), "FeatureCollection")
            features = data.get("features", [])
            self.assertGreater(len(features), 0, f"No features in {geojson_path}")
            for feat in features:
                coords = feat["geometry"]["coordinates"]
                self.assertEqual(len(coords), 2)
                lon, lat = coords
                self.assertTrue(68.0 <= lon <= 98.0, f"Longitude out of India bounds: {lon}")
                self.assertTrue(8.0 <= lat <= 36.0, f"Latitude out of India bounds: {lat}")

    def test_inference_engine_hydrological_context(self):
        from src.inference.predictor import PravahInferenceEngine

        engine = PravahInferenceEngine()
        ctx = engine.get_hydrological_context("684")
        self.assertIn("soil", ctx)
        self.assertIn("river_stage", ctx)
        self.assertIn("terrain", ctx)
        self.assertGreater(ctx["soil"]["scs_curve_number"], 0)
        self.assertGreater(ctx["terrain"]["mean_elevation_m"], 0)

        # Test live prediction includes hydrological_context
        pred = engine.predict_live(
            gauge_id="684",
            rainfall_history_10d=[10.0] * 10,
        )
        self.assertIn("hydrological_context", pred)
        self.assertIn("soil", pred["hydrological_context"])

    def test_api_new_endpoints(self):
        # 1. Dams
        resp = self.client.get("/api/v1/dams")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("type"), "FeatureCollection")
        self.assertGreater(len(resp.json().get("features", [])), 10)

        # 2. River levels
        resp = self.client.get("/api/v1/river-levels?gauge_id=684")
        self.assertEqual(resp.status_code, 200)
        records = resp.json()
        self.assertGreater(len(records), 0)
        self.assertEqual(str(records[0].get("GaugeID")), "684")

        # 3. Terrain
        resp = self.client.get("/api/v1/terrain?gauge_id=684")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.json()), 0)

        # 4. Peaks and passes
        resp = self.client.get("/api/v1/terrain/peaks-passes")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("type"), "FeatureCollection")

        # 5. Soil
        resp = self.client.get("/api/v1/soil?gauge_id=684")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.json()), 0)

        # 6. Confluences
        resp = self.client.get("/api/v1/confluences")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("type"), "FeatureCollection")

        # 7. Disaster response
        resp = self.client.get("/api/v1/disaster-response")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.json()), 0)

        # 8. Safe zones (now contains all registered shelters >= 20)
        resp = self.client.get("/api/safe-zones")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 20)


if __name__ == "__main__":
    unittest.main()
