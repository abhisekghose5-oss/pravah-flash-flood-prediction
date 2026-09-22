"""
PRAVAH — River Gauge Monitoring Module.
Provides real-time river stage observations, thresholds, and trend tracking.
"""

from src.gauges.models.gauge import (
    RiverGauge,
    RiverGaugeStatus,
    RiverTrend,
    RiverGaugeHistoryPoint,
    RiverGaugeObservationRequest,
    ThresholdEvaluationResult,
)
from src.gauges.gauge_service import GaugeService, get_gauge_service

__all__ = [
    "RiverGauge",
    "RiverGaugeStatus",
    "RiverTrend",
    "RiverGaugeHistoryPoint",
    "RiverGaugeObservationRequest",
    "ThresholdEvaluationResult",
    "GaugeService",
    "get_gauge_service",
]
