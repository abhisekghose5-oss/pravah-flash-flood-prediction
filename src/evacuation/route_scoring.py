"""Cost evaluation, travel time computation, and route safety classification."""
import math
from typing import Dict, List, Any
from src.evacuation.models.route import RouteObjective, SafetyClassification
from src.evacuation.evacuation_config import (
    EVACUATION_RISK_WEIGHT,
    EVACUATION_TIME_WEIGHT,
    ROAD_CLOSURE_PENALTY,
    PARTIALLY_BLOCKED_TIME_PENALTY,
    PARTIALLY_BLOCKED_RISK_PENALTY,
    DEFAULT_VEHICLE_SPEED_KMH,
    DEFAULT_WALK_SPEED_KMH,
    RISK_THRESHOLD_LOW,
    RISK_THRESHOLD_MODERATE,
    RISK_THRESHOLD_HIGH,
)


def compute_edge_cost(
    edge: Dict[str, Any],
    objective: RouteObjective = RouteObjective.BALANCED,
    travel_mode: str = "VEHICLE",
) -> float:
    """
    Computes dynamic routing cost for an edge segment based on the objective.
    Returns math.inf if the road segment is CLOSED.
    """
    status = edge.get("status", "OPEN")
    if status == "CLOSED":
        return math.inf

    dist_km = edge.get("distance_km", 1.0)
    base_speed = (
        DEFAULT_WALK_SPEED_KMH
        if travel_mode.upper() == "WALKING"
        else edge.get("base_speed_kmh", DEFAULT_VEHICLE_SPEED_KMH)
    )
    base_time_mins = (dist_km / max(1.0, base_speed)) * 60.0

    raw_risk = edge.get("flood_risk", 0.0)
    partial_penalty_time = 0.0
    effective_risk = raw_risk

    if status == "PARTIALLY_BLOCKED":
        partial_penalty_time = PARTIALLY_BLOCKED_TIME_PENALTY
        effective_risk = min(1.0, effective_risk + PARTIALLY_BLOCKED_RISK_PENALTY)

    # Flood delay (slow speeds through waterlogged segments)
    flood_delay_mins = effective_risk * (5.0 if travel_mode == "VEHICLE" else 10.0)

    if objective == RouteObjective.FASTEST:
        # Prioritize travel time, minor hazard penalty
        return base_time_mins + partial_penalty_time + flood_delay_mins + (effective_risk * 1.5)

    elif objective == RouteObjective.LOWEST_RISK:
        # Prioritize minimum cumulative flood exposure
        risk_penalty = effective_risk * 40.0 * max(0.5, dist_km)
        return (base_time_mins * 0.10) + risk_penalty + partial_penalty_time

    else:  # BALANCED or NEAREST_SHELTER
        # Pareto compromise between transit velocity and hazard mitigation
        risk_penalty = effective_risk * EVACUATION_RISK_WEIGHT * 10.0
        return base_time_mins + partial_penalty_time + flood_delay_mins + risk_penalty


def classify_route_safety(risk_score: float) -> SafetyClassification:
    """Classifies evacuation route safety into standardized tiers."""
    if risk_score <= RISK_THRESHOLD_LOW:
        return SafetyClassification.LOW_RISK
    elif risk_score <= RISK_THRESHOLD_MODERATE:
        return SafetyClassification.MODERATE_RISK
    elif risk_score <= RISK_THRESHOLD_HIGH:
        return SafetyClassification.HIGH_RISK
    else:
        return SafetyClassification.UNSAFE


def compute_route_breakdown(
    edges: List[Dict[str, Any]], travel_mode: str = "VEHICLE"
) -> Dict[str, Any]:
    """
    Computes detailed itemized travel metrics across an edge path sequence.
    """
    if not edges:
        return {
            "distance_km": 0.0,
            "base_time_minutes": 0.0,
            "flood_delay_minutes": 0.0,
            "road_delay_minutes": 0.0,
            "total_time_minutes": 0.0,
            "risk_score": 0.0,
            "safety_classification": SafetyClassification.LOW_RISK,
        }

    total_dist = sum(e.get("distance_km", 0.0) for e in edges)
    base_time = 0.0
    flood_delay = 0.0
    road_delay = 0.0
    weighted_risks = []

    for e in edges:
        d = e.get("distance_km", 0.0)
        speed = (
            DEFAULT_WALK_SPEED_KMH
            if travel_mode.upper() == "WALKING"
            else e.get("base_speed_kmh", DEFAULT_VEHICLE_SPEED_KMH)
        )
        base_time += (d / max(1.0, speed)) * 60.0

        r = e.get("flood_risk", 0.0)
        status = e.get("status", "OPEN")
        eff_risk = r

        if status == "PARTIALLY_BLOCKED":
            road_delay += PARTIALLY_BLOCKED_TIME_PENALTY
            eff_risk = min(1.0, eff_risk + PARTIALLY_BLOCKED_RISK_PENALTY)

        flood_delay += eff_risk * (12.0 if travel_mode == "VEHICLE" else 20.0)
        weighted_risks.append(eff_risk * max(0.1, d))

    total_time = round(base_time + flood_delay + road_delay, 1)
    cum_risk = sum(weighted_risks) / max(0.1, total_dist)
    final_risk_score = round(min(1.0, max(0.0, cum_risk)), 3)

    return {
        "distance_km": round(total_dist, 2),
        "base_time_minutes": round(base_time, 1),
        "flood_delay_minutes": round(flood_delay, 1),
        "road_delay_minutes": round(road_delay, 1),
        "total_time_minutes": total_time,
        "risk_score": final_risk_score,
        "safety_classification": classify_route_safety(final_risk_score),
    }
