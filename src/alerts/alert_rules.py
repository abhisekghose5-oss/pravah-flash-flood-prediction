"""
PRAVAH — Alert Trigger Rules Engine
Evaluates hydrological telemetry (Risk Score > 70%, River Stage Thresholds,
and Heavy Rainfall Forecast) to determine alert trigger eligibility and severity.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from src.alerts.models.alert import AlertSeverity, TriggerType

# Configurable trigger thresholds via environment variables
RISK_ALERT_THRESHOLD: float = float(os.getenv("RISK_ALERT_THRESHOLD", "70.0"))
RIVER_WARNING_THRESHOLD: float = float(os.getenv("RIVER_WARNING_THRESHOLD", "8.0"))
RIVER_CRITICAL_THRESHOLD: float = float(os.getenv("RIVER_CRITICAL_THRESHOLD", "9.0"))
RAINFALL_ALERT_THRESHOLD: float = float(os.getenv("RAINFALL_ALERT_THRESHOLD", "150.0"))


@dataclass
class AlertEvaluationResult:
    """Result of rule evaluation for flood hazard triggers."""
    is_triggered: bool
    severity: AlertSeverity
    trigger_type: TriggerType
    trigger_reason: str
    risk_percentage: int


def evaluate_alert_rules(
    risk_score: Optional[float] = None,
    river_level: Optional[float] = None,
    river_threshold: Optional[float] = None,
    rainfall_forecast: Optional[float] = None,
    explicit_severity: Optional[AlertSeverity] = None,
) -> AlertEvaluationResult:
    """
    Evaluates incoming telemetry against flood risk criteria.

    Rules hierarchy:
    1. Evacuation: River level >= critical + 0.5m OR Risk >= 90%
    2. Critical: River level >= critical threshold OR Risk >= 80% OR (Rainfall > 200mm AND Risk > 70%)
    3. Warning: River level >= warning threshold OR Risk > 70% OR Rainfall >= 150mm
    """
    # 0. Handle explicit severity override (for manual test triggers)
    if explicit_severity:
        norm_risk = int(risk_score * 100) if (risk_score and risk_score <= 1.0) else int(risk_score or 75)
        return AlertEvaluationResult(
            is_triggered=True,
            severity=explicit_severity,
            trigger_type=TriggerType.MANUAL_DISPATCH,
            trigger_reason=f"Manual dispatch initiated at severity {explicit_severity.value}.",
            risk_percentage=norm_risk,
        )

    # Normalize risk score to integer percentage [0, 100]
    norm_risk = 0
    if risk_score is not None:
        norm_risk = int(risk_score * 100) if risk_score <= 1.0 else int(risk_score)

    warn_threshold = river_threshold if river_threshold is not None else RIVER_WARNING_THRESHOLD
    crit_threshold = RIVER_CRITICAL_THRESHOLD

    reasons = []
    highest_severity: Optional[AlertSeverity] = None
    primary_trigger = TriggerType.MANUAL_DISPATCH

    # Rule 1: River Level Trigger
    if river_level is not None:
        if river_level >= crit_threshold + 0.5:
            reasons.append(f"River level ({river_level:.1f}m) has breached catastrophic evacuation mark ({crit_threshold + 0.5:.1f}m)")
            highest_severity = AlertSeverity.EVACUATION
            primary_trigger = TriggerType.RIVER_LEVEL
        elif river_level >= crit_threshold:
            reasons.append(f"River level ({river_level:.1f}m) exceeded critical stage ({crit_threshold:.1f}m)")
            if highest_severity != AlertSeverity.EVACUATION:
                highest_severity = AlertSeverity.CRITICAL
            primary_trigger = TriggerType.RIVER_LEVEL
        elif river_level >= warn_threshold:
            reasons.append(f"River level ({river_level:.1f}m) exceeded warning stage ({warn_threshold:.1f}m)")
            if not highest_severity:
                highest_severity = AlertSeverity.WARNING
            primary_trigger = TriggerType.RIVER_LEVEL

    # Rule 2: Risk Score Trigger (> 70%)
    if norm_risk >= 90:
        reasons.append(f"AI flood onset risk ({norm_risk}%) reached catastrophic emergency tier")
        highest_severity = AlertSeverity.EVACUATION
        primary_trigger = TriggerType.RISK_SCORE
    elif norm_risk >= 80:
        reasons.append(f"AI flood onset risk ({norm_risk}%) reached critical danger tier")
        if highest_severity != AlertSeverity.EVACUATION:
            highest_severity = AlertSeverity.CRITICAL
        primary_trigger = TriggerType.RISK_SCORE
    elif norm_risk >= RISK_ALERT_THRESHOLD:
        reasons.append(f"AI flood onset risk ({norm_risk}%) exceeded alert threshold ({RISK_ALERT_THRESHOLD:.0f}%)")
        if not highest_severity:
            highest_severity = AlertSeverity.WARNING
        primary_trigger = TriggerType.RISK_SCORE

    # Rule 3: Heavy Rainfall Forecast Trigger
    if rainfall_forecast is not None and rainfall_forecast >= RAINFALL_ALERT_THRESHOLD:
        reasons.append(f"Extreme forecast rainfall ({rainfall_forecast:.0f}mm) exceeds threshold ({RAINFALL_ALERT_THRESHOLD:.0f}mm)")
        if not highest_severity:
            highest_severity = AlertSeverity.WARNING
        elif highest_severity == AlertSeverity.WARNING and rainfall_forecast >= 200.0:
            highest_severity = AlertSeverity.CRITICAL
        if primary_trigger == TriggerType.MANUAL_DISPATCH:
            primary_trigger = TriggerType.RAINFALL_FORECAST

    if len(reasons) > 1:
        primary_trigger = TriggerType.MULTI_FACTOR

    is_triggered = (highest_severity is not None)

    return AlertEvaluationResult(
        is_triggered=is_triggered,
        severity=highest_severity or AlertSeverity.WARNING,
        trigger_type=primary_trigger,
        trigger_reason=" • ".join(reasons) if reasons else "No active flood hazard triggers detected.",
        risk_percentage=norm_risk,
    )
