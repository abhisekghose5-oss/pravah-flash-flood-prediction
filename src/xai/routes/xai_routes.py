from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from src.xai.models.explanation import (
    ExplanationRequest,
    ExplanationResponse,
    FeatureImportanceResponse,
    ForcePlotData,
    GlobalSummaryResponse,
    SupportedModelsResponse,
)
from src.xai.xai_manager import XAIManager

logger = logging.getLogger("pravah.xai.routes")

router = APIRouter(prefix="/api/xai", tags=["Explainable AI (XAI)"])


@router.get("/models", response_model=SupportedModelsResponse)
def get_xai_models() -> SupportedModelsResponse:
    """
    Retrieve operational status and SHAP explainer configurations
    for all supported ML models (Random Forest, XGBoost, LightGBM).
    """
    manager = XAIManager.get_instance()
    return manager.get_supported_models()


@router.post("/explain", response_model=ExplanationResponse)
def explain_prediction(request: ExplanationRequest) -> ExplanationResponse:
    """
    Generate on-demand SHAP explanation for an individual prediction.
    Explains which features contributed positively or negatively to the flood onset risk.
    """
    manager = XAIManager.get_instance()
    resp = manager.explain(request)
    if resp.status == "error":
        logger.warning("XAI returned error status: %s", resp.headline_narrative)
    return resp


@router.get("/summary", response_model=GlobalSummaryResponse)
def get_global_summary(
    model: Optional[str] = Query("RandomForest", description="Model architecture: 'RandomForest', 'XGBoost', or 'LightGBM'"),
    task: Optional[str] = Query("onset", description="'onset' (Task A) or 'active' (Task B)"),
) -> GlobalSummaryResponse:
    """
    Retrieve global SHAP summary plot distribution across representative catchment profiles.
    Illustrates overall model feature attribution and directional sensitivity.
    """
    manager = XAIManager.get_instance()
    return manager.get_summary(model_name=model or "RandomForest", task=task or "onset")


@router.get("/feature-importance", response_model=FeatureImportanceResponse)
def get_feature_importance(
    model: Optional[str] = Query("RandomForest", description="Model architecture: 'RandomForest', 'XGBoost', or 'LightGBM'"),
    task: Optional[str] = Query("onset", description="'onset' (Task A) or 'active' (Task B)"),
) -> FeatureImportanceResponse:
    """
    Retrieve ranked global feature importance computed via mean absolute SHAP values.
    """
    manager = XAIManager.get_instance()
    return manager.get_feature_importance(model_name=model or "RandomForest", task=task or "onset")


@router.post("/force-plot", response_model=ForcePlotData)
def get_force_plot(request: ExplanationRequest) -> ForcePlotData:
    """
    Generate SHAP Force Plot data and pre-rendered SVG visualization for a prediction.
    """
    manager = XAIManager.get_instance()
    return manager.get_force_plot(request)
