from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    """Detailed SHAP contribution metrics for a single input feature."""
    feature_key: str = Field(..., description="Raw or preprocessed feature key")
    feature_name: str = Field(..., description="Human-readable feature name")
    feature_value: Any = Field(..., description="Input feature value observed")
    shap_value: float = Field(..., description="Raw SHAP contribution value")
    direction: str = Field(..., description="'increases_risk' or 'decreases_risk'")
    relative_contribution: float = Field(
        ..., description="Normalized contribution percentage (0-100%) based on total absolute SHAP mass"
    )
    unit: str = Field("", description="Engineering or physical unit (e.g. 'mm', 'm', '°', '%')")
    domain_category: str = Field(
        "other", description="Domain classification ('precipitation', 'hydrology', 'topography', 'geospatial')"
    )
    human_explanation: str = Field(..., description="Contextual narrative explanation of the factor's impact")


class ForcePlotData(BaseModel):
    """Telemetry and visual markers for rendering a SHAP Force Plot."""
    base_value: float = Field(..., description="Expected model baseline output E[f(x)]")
    output_value: float = Field(..., description="Final model predicted probability or score")
    total_positive_force: float = Field(..., description="Sum of positive SHAP forces pushing risk up")
    total_negative_force: float = Field(..., description="Sum of negative SHAP forces pulling risk down")
    positive_features: List[FeatureContribution] = Field(default_factory=list)
    negative_features: List[FeatureContribution] = Field(default_factory=list)
    svg_markup: Optional[str] = Field(None, description="Pre-rendered SVG visualization snippet")


class ExplanationRequest(BaseModel):
    """Request payload to generate a local prediction explanation."""
    gauge_id: Optional[str] = Field(None, description="Target gauge ID (e.g. '684' or 'INDOFLOODS-gauge-684')")
    station_id: Optional[str] = Field(None, description="Station alias or Northeast station name (e.g. 'Beki')")
    region: Optional[str] = Field("maharashtra", description="'maharashtra' or 'northeast'")
    rainfall_history_10d: Optional[List[float]] = Field(
        None, description="10 daily rainfall amounts (mm) in chronological order: [P_{T-10}, ..., P_{T-1}]"
    )
    model_name: Optional[str] = Field(
        "RandomForest", description="ML Model architecture ('RandomForest', 'XGBoost', or 'LightGBM')"
    )
    task: Optional[str] = Field("onset", description="'onset' (Task A) or 'active' (Task B)")
    custom_features: Optional[Dict[str, Any]] = Field(
        None, description="Optional explicit feature dictionary overriding standard gauge attributes"
    )


class ExplanationResponse(BaseModel):
    """Response payload containing comprehensive local prediction explanations."""
    status: str = Field("success", description="Status code ('success' or 'error')")
    model_used: str = Field(..., description="Exact model bundle used for explanation")
    task: str = Field("onset", description="Flood prediction task explained")
    station_name: str = Field("Unknown", description="Target river gauge or station name")
    prediction_probability: float = Field(..., description="Predicted flood risk probability [0.0, 1.0]")
    decision_threshold: float = Field(..., description="Calibrated decision threshold for alert triggering")
    risk_level: str = Field(..., description="Alert classification ('EMERGENCY', 'WARNING', 'ADVISORY', 'NORMAL')")
    headline_title: str = Field(..., description="Header narrative title (e.g. 'WHY HIGH RISK?')")
    headline_narrative: str = Field(..., description="Natural-language summary explaining the prediction")
    base_value: float = Field(..., description="Expected base prediction probability")
    top_contributing_factors: List[FeatureContribution] = Field(
        default_factory=list, description="Primary features driving flood risk higher"
    )
    top_reducing_factors: List[FeatureContribution] = Field(
        default_factory=list, description="Primary features keeping flood risk lower"
    )
    all_contributions: List[FeatureContribution] = Field(
        default_factory=list, description="All evaluated features ordered by impact magnitude"
    )
    force_plot: ForcePlotData = Field(..., description="SHAP Force Plot data structure")
    disclaimer: str = Field(
        "XAI explanations show which model inputs contributed to the prediction. They should not be interpreted as proof of direct causation.",
        description="Mandatory interpretability notice",
    )


class GlobalSummaryFeature(BaseModel):
    """Global feature impact summary across catchments."""
    feature_key: str = Field(..., description="Technical feature identifier")
    feature_name: str = Field(..., description="Human-friendly label")
    mean_abs_shap: float = Field(..., description="Mean absolute SHAP value across reference distribution")
    relative_importance: float = Field(..., description="Percentage of total feature attribution")
    correlation: str = Field("positive", description="'positive' (higher value -> higher risk) or 'negative'")
    domain_category: str = Field("other")
    sample_values: List[float] = Field(default_factory=list)
    sample_shaps: List[float] = Field(default_factory=list)


class GlobalSummaryResponse(BaseModel):
    """Response payload for global SHAP summary plot distribution."""
    status: str = Field("success")
    model_used: str = Field(...)
    task: str = Field("onset")
    top_features: List[GlobalSummaryFeature] = Field(default_factory=list)
    sample_size: int = Field(..., description="Number of background instances evaluated")
    disclaimer: str = Field(
        "Global SHAP summary illustrates overall model sensitivity across representative catchment profiles."
    )


class FeatureImportanceItem(BaseModel):
    """Ranked global feature importance entry."""
    rank: int = Field(..., description="Rank (1 = highest influence)")
    feature_key: str = Field(...)
    feature_name: str = Field(...)
    importance_score: float = Field(..., description="Mean absolute SHAP attribution")
    relative_importance_percent: float = Field(..., description="Share of total model attribution (%)")
    domain_category: str = Field("other")


class FeatureImportanceResponse(BaseModel):
    """Response payload for global feature importance graph."""
    status: str = Field("success")
    model_used: str = Field(...)
    task: str = Field("onset")
    features: List[FeatureImportanceItem] = Field(default_factory=list)


class SupportedModelItem(BaseModel):
    """Information regarding a supported explainable ML model."""
    model_id: str
    display_name: str
    algorithm: str
    explainer_type: str
    is_available: bool
    description: str


class SupportedModelsResponse(BaseModel):
    """Response payload listing supported explainable models."""
    status: str = Field("success")
    supported_models: List[SupportedModelItem] = Field(default_factory=list)
