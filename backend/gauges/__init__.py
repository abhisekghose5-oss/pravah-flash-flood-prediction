"""
PRAVAH River Gauge Monitoring — Backward Compatibility Proxy.
Re-exports GaugeService and models from src.gauges.
"""

from src.gauges import (
    RiverGauge,
    RiverGaugeStatus,
    RiverTrend,
    RiverGaugeHistoryPoint,
    RiverGaugeObservationRequest,
    ThresholdEvaluationResult,
    GaugeService,
    get_gauge_service,
)

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
