"""River Gauge models package."""

from src.gauges.models.gauge import (
    RiverGauge,
    RiverGaugeStatus,
    RiverTrend,
    RiverGaugeHistoryPoint,
    RiverGaugeObservationRequest,
    ThresholdEvaluationResult,
)

__all__ = [
    "RiverGauge",
    "RiverGaugeStatus",
    "RiverTrend",
    "RiverGaugeHistoryPoint",
    "RiverGaugeObservationRequest",
    "ThresholdEvaluationResult",
]
