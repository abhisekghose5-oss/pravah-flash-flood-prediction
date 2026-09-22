from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.api.app import app
from src.inference.predictor import PravahInferenceEngine
from src.xai.explainer_factory import ExplainerFactory
from src.xai.explainers.lightgbm_explainer import LightGBMExplainer
from src.xai.explainers.random_forest_explainer import RandomForestExplainer
from src.xai.explainers.xgboost_explainer import XGBoostExplainer
from src.xai.explanation_service import XAIExplanationService
from src.xai.feature_mapper import FeatureMapper
from src.xai.models.explanation import ExplanationRequest, ForcePlotData
from src.xai.shap_utils import (
    build_feature_contributions,
    build_force_plot_data,
    compute_relative_contributions,
    generate_headline_narrative,
)
from src.xai.utils.visualization import render_feature_importance_svg, render_force_plot_svg
from src.xai.xai_manager import XAIManager


class TestExplainableAIModule(unittest.TestCase):
    """Comprehensive test suite validating the PRAVAH Explainable AI (XAI) subsystem."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.engine = PravahInferenceEngine()
        cls.service = XAIExplanationService(engine=cls.engine)
        cls.manager = XAIManager(service=cls.service)

    def test_feature_mapper_clean_keys(self):
        """Test transformer prefix removal."""
        self.assertEqual(FeatureMapper.clean_key("num__rain_1d"), "rain_1d")
        self.assertEqual(FeatureMapper.clean_key("cat__State_Maharashtra"), "State_Maharashtra")
        self.assertEqual(FeatureMapper.clean_key("Slope"), "Slope")

    def test_feature_mapper_metadata(self):
        """Test human-friendly names, units, and domain categories."""
        name, unit, cat = FeatureMapper.get_metadata("num__rain_1d")
        self.assertEqual(name, "24-Hour Rainfall")
        self.assertEqual(unit, "mm")
        self.assertEqual(cat, "precipitation")

        name, unit, cat = FeatureMapper.get_metadata("num__Warning_Level")
        self.assertEqual(name, "River Warning Threshold")
        self.assertEqual(unit, "m")
        self.assertEqual(cat, "hydrology")

        name, unit, cat = FeatureMapper.get_metadata("Slope")
        self.assertEqual(unit, "°")
        self.assertEqual(cat, "topography")

    def test_feature_mapper_human_explanation(self):
        """Test dynamic natural language factor explanation generation."""
        expl_pos = FeatureMapper.generate_human_explanation(
            "24-Hour Rainfall", 85.0, 0.25, "increases_risk", "mm"
        )
        self.assertIn("85.00 mm", expl_pos)
        self.assertIn("saturated", expl_pos.lower())

        expl_neg = FeatureMapper.generate_human_explanation(
            "24-Hour Rainfall", 2.0, -0.15, "decreases_risk", "mm"
        )
        self.assertIn("2.00 mm", expl_neg)
        self.assertIn("suppressed", expl_neg.lower())

    def test_relative_contributions_calculation(self):
        """Test normalized relative contribution percentages."""
        shaps = np.array([0.40, -0.20, 0.10, -0.30])
        rel_pct = compute_relative_contributions(shaps)
        # Sum of absolute = 0.4 + 0.2 + 0.1 + 0.3 = 1.0 -> 40%, 20%, 10%, 30%
        self.assertAlmostEqual(float(np.sum(rel_pct)), 100.0, places=1)
        self.assertAlmostEqual(rel_pct[0], 40.0, places=1)
        self.assertAlmostEqual(rel_pct[1], 20.0, places=1)

        # Zero handling
        zero_shaps = np.array([0.0, 0.0, 0.0])
        zero_pct = compute_relative_contributions(zero_shaps)
        self.assertEqual(list(zero_pct), [0.0, 0.0, 0.0])

    def test_headline_narrative_generation(self):
        """Test generation of WHY HIGH RISK vs WHY LOW RISK narratives."""
        contributions = build_feature_contributions(
            feature_names=["num__rain_1d", "num__Warning_Level"],
            shap_values=np.array([0.35, -0.10]),
            input_values={"rain_1d": 120.0, "Warning_Level": 6.5},
        )
        pos = [c for c in contributions if c.shap_value > 0]
        neg = [c for c in contributions if c.shap_value < 0]

        # High Risk
        title_high, narr_high = generate_headline_narrative(0.85, 0.30, "EMERGENCY", pos, neg)
        self.assertEqual(title_high, "WHY HIGH RISK?")
        self.assertIn("85.0%", narr_high)
        self.assertIn("24-Hour Rainfall", narr_high)

        # Moderate Risk
        title_mod, narr_mod = generate_headline_narrative(0.20, 0.30, "ADVISORY", pos, neg)
        self.assertEqual(title_mod, "WHY MODERATE RISK?")

        # Low Risk
        title_low, narr_low = generate_headline_narrative(0.05, 0.30, "NORMAL", pos, neg)
        self.assertEqual(title_low, "WHY LOW RISK?")
        self.assertIn("5.0%", narr_low)

    def test_explainer_factory_caching(self):
        """Test explainer factory caching and retrieval."""
        ExplainerFactory.clear_cache()
        bundle = self.engine._models["task_a_onset_RandomForest"]
        pipe = bundle["model"]
        pre = pipe.named_steps["preprocessor"]
        clf = pipe.named_steps["classifier"]
        feat_names = list(pre.get_feature_names_out())

        exp1 = ExplainerFactory.get_explainer("RandomForest", clf, feat_names, "onset")
        self.assertIsInstance(exp1, RandomForestExplainer)

        exp2 = ExplainerFactory.get_explainer("RandomForest", clf, feat_names, "onset")
        self.assertIs(exp1, exp2)  # Exact same cached instance

        # Unsupported model
        with self.assertRaises(ValueError):
            ExplainerFactory.get_explainer("UnsupportedNeuralNet", object(), feat_names, "onset")

    def test_random_forest_explainer(self):
        """Test RandomForestExplainer explanation on real bundle."""
        bundle = self.engine._models["task_a_onset_RandomForest"]
        pipe = bundle["model"]
        pre = pipe.named_steps["preprocessor"]
        clf = pipe.named_steps["classifier"]
        feat_names = list(pre.get_feature_names_out())

        explainer = RandomForestExplainer(clf, feat_names)
        req = ExplanationRequest(
            gauge_id="684",
            rainfall_history_10d=[0.0, 5.0, 15.0, 30.0, 60.0, 85.0, 110.0, 40.0, 15.0, 50.0],
            model_name="RandomForest",
        )
        df_raw, _, raw_dict = self.service._prepare_input_dataframe(req, bundle["feature_cols"])
        X_trans = pre.transform(df_raw)

        prob, shaps, base_val = explainer.explain_instance(X_trans, raw_dict)
        self.assertIsInstance(prob, float)
        self.assertTrue(0.0 <= prob <= 1.0)
        self.assertEqual(len(shaps), len(feat_names))
        self.assertIsInstance(base_val, float)

    def test_xgboost_explainer(self):
        """Test XGBoostExplainer explanation on real bundle."""
        bundle = self.engine._models["task_a_onset_XGBoost"]
        pipe = bundle["model"]
        pre = pipe.named_steps["preprocessor"]
        clf = pipe.named_steps["classifier"]
        feat_names = list(pre.get_feature_names_out())

        explainer = XGBoostExplainer(clf, feat_names)
        req = ExplanationRequest(
            gauge_id="684",
            rainfall_history_10d=[10.0, 20.0, 35.0, 50.0, 75.0, 95.0, 120.0, 80.0, 45.0, 90.0],
            model_name="XGBoost",
        )
        df_raw, _, raw_dict = self.service._prepare_input_dataframe(req, bundle["feature_cols"])
        X_trans = pre.transform(df_raw)

        prob, shaps, base_val = explainer.explain_instance(X_trans, raw_dict)
        self.assertIsInstance(prob, float)
        self.assertTrue(0.0 <= prob <= 1.0)
        self.assertEqual(len(shaps), len(feat_names))

    def test_lightgbm_explainer(self):
        """Test LightGBMExplainer explanation on real bundle."""
        bundle = self.engine._models["task_a_onset_LightGBM"]
        pipe = bundle["model"]
        pre = pipe.named_steps["preprocessor"]
        clf = pipe.named_steps["classifier"]
        feat_names = list(pre.get_feature_names_out())

        explainer = LightGBMExplainer(clf, feat_names)
        req = ExplanationRequest(
            gauge_id="684",
            rainfall_history_10d=[20.0, 30.0, 50.0, 70.0, 95.0, 120.0, 150.0, 90.0, 60.0, 110.0],
            model_name="LightGBM",
        )
        df_raw, _, raw_dict = self.service._prepare_input_dataframe(req, bundle["feature_cols"])
        X_trans = pre.transform(df_raw)

        prob, shaps, base_val = explainer.explain_instance(X_trans, raw_dict)
        self.assertIsInstance(prob, float)
        self.assertTrue(0.0 <= prob <= 1.0)
        self.assertEqual(len(shaps), len(feat_names))

    def test_force_plot_svg_rendering(self):
        """Test SHAP Force Plot SVG rendering."""
        force_data = ForcePlotData(
            base_value=0.25,
            output_value=0.78,
            total_positive_force=0.60,
            total_negative_force=-0.07,
            positive_features=[],
            negative_features=[],
        )
        svg = render_force_plot_svg(force_data)
        self.assertIn("<svg", svg)
        self.assertIn("Base 0.25", svg)
        self.assertIn("78.0%", svg)
        self.assertIn("posGrad", svg)

    def test_feature_importance_svg_rendering(self):
        """Test Feature Importance SVG rendering."""
        features = self.service.get_global_feature_importance("RandomForest").features
        svg = render_feature_importance_svg(features)
        self.assertIn("<svg", svg)
        self.assertIn(features[0].feature_name[:10], svg)

    def test_api_xai_models_endpoint(self):
        """Test GET /api/xai/models endpoint."""
        resp = self.client.get("/api/xai/models")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        models = data["supported_models"]
        model_ids = [m["model_id"] for m in models]
        self.assertIn("RandomForest", model_ids)
        self.assertIn("XGBoost", model_ids)
        self.assertIn("LightGBM", model_ids)

    def test_api_xai_explain_endpoint_random_forest(self):
        """Test POST /api/xai/explain with RandomForest."""
        payload = {
            "gauge_id": "684",
            "rainfall_history_10d": [0.0, 5.0, 15.0, 30.0, 55.0, 80.0, 110.0, 45.0, 20.0, 65.0],
            "model_name": "RandomForest",
            "task": "onset",
        }
        resp = self.client.post("/api/xai/explain", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("task_a_onset_RandomForest", data["model_used"])
        self.assertGreater(len(data["all_contributions"]), 10)
        self.assertIsNotNone(data["force_plot"]["svg_markup"])

    def test_api_xai_explain_endpoint_xgboost(self):
        """Test POST /api/xai/explain with XGBoost."""
        payload = {
            "gauge_id": "685",
            "rainfall_history_10d": [25.0, 40.0, 65.0, 90.0, 120.0, 140.0, 160.0, 95.0, 60.0, 85.0],
            "model_name": "XGBoost",
            "task": "onset",
        }
        resp = self.client.post("/api/xai/explain", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("task_a_onset_XGBoost", data["model_used"])
        self.assertIn("WHY", data["headline_title"])

    def test_api_xai_feature_importance_endpoint(self):
        """Test GET /api/xai/feature-importance."""
        resp = self.client.get("/api/xai/feature-importance?model=XGBoost")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertGreater(len(data["features"]), 50)
        # Verify rank 1 is highest importance
        self.assertEqual(data["features"][0]["rank"], 1)
        self.assertGreaterEqual(
            data["features"][0]["importance_score"], data["features"][1]["importance_score"]
        )

    def test_api_xai_summary_endpoint(self):
        """Test GET /api/xai/summary."""
        resp = self.client.get("/api/xai/summary?model=LightGBM")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["top_features"]), 8)

    def test_api_xai_force_plot_endpoint(self):
        """Test POST /api/xai/force-plot."""
        payload = {
            "gauge_id": "684",
            "rainfall_history_10d": [5.0, 10.0, 15.0, 20.0, 30.0, 45.0, 60.0, 25.0, 15.0, 20.0],
            "model_name": "RandomForest",
        }
        resp = self.client.post("/api/xai/force-plot", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("base_value", data)
        self.assertIn("output_value", data)
        self.assertIsNotNone(data["svg_markup"])

    def test_failure_isolation_shap_error(self):
        """
        Verify that an internal XAI exception fails safely within the XAI boundary,
        returning an error status payload rather than crashing the process.
        """
        with patch.object(self.service, "explain_prediction", side_effect=RuntimeError("Simulated SHAP Crash")):
            req = ExplanationRequest(gauge_id="684", model_name="RandomForest")
            resp = self.manager.explain(req)
            self.assertEqual(resp.status, "error")
            self.assertIn("EXPLANATION TEMPORARILY UNAVAILABLE", resp.headline_title)

    def test_legacy_prediction_api_untouched(self):
        """
        Verify that existing ML inference endpoints remain 100% operational
        and completely unaffected by the XAI integration.
        """
        payload = {
            "gauge_id": "684",
            "rainfall_history_10d": [0.0, 2.5, 8.0, 15.2, 45.0, 92.5, 110.0, 35.0, 12.0, 28.4],
            "onset_model": "RandomForest",
            "active_model": "XGBoost",
        }
        resp = self.client.post("/api/v1/predict/live", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("task_a_onset", data)
        self.assertIn("task_b_active", data)
        self.assertIn("alert_tier", data)


if __name__ == "__main__":
    unittest.main()
