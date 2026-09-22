from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from src.xai.explanation_service import XAIExplanationService
from src.xai.models.explanation import (
    ExplanationRequest,
    ExplanationResponse,
    FeatureImportanceResponse,
    ForcePlotData,
    GlobalSummaryResponse,
    SupportedModelsResponse,
)

logger = logging.getLogger("pravah.xai.manager")


class XAIManager:
    """
    Central Explainable AI Orchestrator for PRAVAH.
    Coordinates explainer discovery, local prediction explanations, global feature
    importance ranking, and visual force plot data preparation.
    """

    _instance: Optional[XAIManager] = None
    _lock = threading.Lock()

    def __init__(self, service: Optional[XAIExplanationService] = None):
        self.service = service or XAIExplanationService()

    @classmethod
    def get_instance(cls) -> XAIManager:
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def explain(self, request: ExplanationRequest) -> ExplanationResponse:
        """
        Generate a local prediction explanation for an individual observation.
        Fails safely if an unexpected exception occurs.
        """
        try:
            return self.service.explain_prediction(request)
        except Exception as e:
            logger.error("XAI local explanation error: %s", e, exc_info=True)
            # Safe fallback explanation avoiding hard failure
            fallback_title = "EXPLANATION TEMPORARILY UNAVAILABLE"
            fallback_narrative = (
                f"SHAP explanation generation encountered an issue ({type(e).__name__}: {str(e)}). "
                "Primary flood prediction workflows remain fully operational."
            )
            return ExplanationResponse(
                status="error",
                model_used=request.model_name or "Unknown",
                task=request.task or "onset",
                station_name="Unknown",
                prediction_probability=0.0,
                decision_threshold=0.30,
                risk_level="NORMAL",
                headline_title=fallback_title,
                headline_narrative=fallback_narrative,
                base_value=0.0,
                top_contributing_factors=[],
                top_reducing_factors=[],
                all_contributions=[],
                force_plot=ForcePlotData(
                    base_value=0.0,
                    output_value=0.0,
                    total_positive_force=0.0,
                    total_negative_force=0.0,
                    positive_features=[],
                    negative_features=[],
                    svg_markup=None,
                ),
            )

    def get_feature_importance(
        self, model_name: str = "RandomForest", task: str = "onset"
    ) -> FeatureImportanceResponse:
        """Retrieve global feature importance ranking for the specified model."""
        try:
            return self.service.get_global_feature_importance(model_name, task)
        except Exception as e:
            logger.error("XAI global feature importance error: %s", e, exc_info=True)
            return FeatureImportanceResponse(
                status="error",
                model_used=model_name,
                task=task,
                features=[],
            )

    def get_summary(
        self, model_name: str = "RandomForest", task: str = "onset"
    ) -> GlobalSummaryResponse:
        """Retrieve global SHAP summary plot distribution across catchments."""
        try:
            return self.service.get_global_summary(model_name, task)
        except Exception as e:
            logger.error("XAI global summary error: %s", e, exc_info=True)
            return GlobalSummaryResponse(
                status="error",
                model_used=model_name,
                task=task,
                top_features=[],
                sample_size=0,
            )

    def get_force_plot(self, request: ExplanationRequest) -> ForcePlotData:
        """Generate force plot data structure and SVG markup for a prediction."""
        explanation = self.explain(request)
        return explanation.force_plot

    def get_supported_models(self) -> SupportedModelsResponse:
        """List all supported explainable ML architectures."""
        return self.service.get_supported_models()
