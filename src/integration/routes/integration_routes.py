"""
PRAVAH — Central Platform Integration Router.
Provides consolidated workflows and unified health diagnostics connecting:
1. River Gauge Monitoring
2. SMS Alert System
3. WhatsApp Alert System
4. Telegram Alert System
5. IVRS Voice Calling System
6. Evacuation Planning Engine
7. Explainable AI (XAI) Engine
8. Digital Twin Studio
9. Flood Propagation Simulator
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.evacuation.models.route import RouteObjective
from src.integration.platform_orchestrator import get_platform_orchestrator
from src.simulation.models.scenario import (
    DamReleaseScenarioParams,
    RiverOverflowScenarioParams,
    RainfallScenarioParams,
    ScenarioType,
    SimulationPeriod,
    SpatialDistribution,
)
from src.simulation.models.simulation import SimulationRunRequest

router = APIRouter(prefix="/api/integration", tags=["Platform Integration & Workflows"])


class RiverThresholdAlertRequest(BaseModel):
    gauge_id: str = Field(..., description="Target river gauge ID (e.g., '684' or 'NE-Beki')")
    simulated_level_m: Optional[float] = Field(None, description="Optional override stage height in meters for threshold testing")
    channels: Optional[List[str]] = Field(None, description="Channels to dispatch ('sms', 'whatsapp', 'telegram', 'ivrs'). Defaults to all enabled.")
    custom_recipient: Optional[str] = Field(None, description="Optional test phone number or telegram chat ID")


class PredictAndExplainRequest(BaseModel):
    gauge_id: str = Field(..., description="Target gauge ID")
    rainfall_history_10d: List[float] = Field(..., description="10-day rainfall sequence in mm")
    onset_model: str = Field("RandomForest", description="ML model for flood onset ('RandomForest', 'XGBoost', 'LightGBM')")
    active_model: str = Field("XGBoost", description="ML model for active flooding ('RandomForest', 'XGBoost', 'LightGBM')")
    explain: bool = Field(True, description="Whether to generate SHAP feature explanations")
    region: Optional[str] = Field(None, description="Geographic region ('Maharashtra' or 'Northeast')")


class SimulationEvacuationRequest(BaseModel):
    origin_lat: float = Field(..., description="Starting latitude for evacuation (e.g. 17.289)")
    origin_lng: float = Field(..., description="Starting longitude for evacuation (e.g. 74.181)")
    preferred_objective: RouteObjective = Field(RouteObjective.LOWEST_RISK, description="Routing goal: lowest_risk, shortest_distance, fastest_time")
    scenario_type: ScenarioType = Field(ScenarioType.RAINFALL, description="Simulation scenario type: rainfall, dam_release, river_overflow")
    simulation_period_hours: SimulationPeriod = Field(SimulationPeriod.PERIOD_6H, description="Simulation time horizon (hours)")
    rainfall_mm: Optional[float] = Field(120.0, description="Total rainfall for rainfall scenario (mm)")
    catchment_id: Optional[str] = Field("684", description="Target basin catchment ID")


class EndToEndWorkflowRequest(BaseModel):
    gauge_id: str = Field("684", description="Station/gauge ID to run full lifecycle for")
    rainfall_10d: Optional[List[float]] = Field(
        None,
        description="10-day daily precipitation series (mm). If omitted, standard monsoon profile is used."
    )
    recipient_phone: Optional[str] = Field(None, description="Recipient phone number for alert notifications")
    channels: Optional[List[str]] = Field(None, description="Channels to alert ('sms', 'whatsapp', 'telegram', 'ivrs')")


@router.get("/health", summary="Unified Platform Subsystems Health")
def get_unified_health() -> Dict[str, Any]:
    """
    Returns aggregated operational status across all 9 PRAVAH subsystems,
    active alerting channels, and SQLite persistence migrations.
    """
    orchestrator = get_platform_orchestrator()
    return orchestrator.get_unified_health()


@router.get("/modules", summary="Catalog of Integrated Subsystems")
def list_integrated_modules() -> Dict[str, Any]:
    """
    Returns full metadata for all 9 integrated modules in the PRAVAH architecture,
    including their primary REST prefixes, responsibilities, and statuses.
    """
    return {
        "platform": "PRAVAH Flood Early-Warning Platform",
        "total_modules": 9,
        "modules": [
            {
                "id": "river_gauge_monitoring",
                "name": "River Gauge Monitoring Module",
                "prefix": "/api/gauges",
                "responsibility": "Real-time river level observation, warning/danger threshold checks, rate-of-rise metrics.",
                "status": "ONLINE"
            },
            {
                "id": "sms_alert_system",
                "name": "SMS Alert Delivery Channel",
                "prefix": "/api/alerts",
                "responsibility": "Cellular SMS broadcast via Twilio / mock sandbox mode for emergency notifications.",
                "status": "ONLINE"
            },
            {
                "id": "whatsapp_alert_system",
                "name": "WhatsApp Alert Delivery Channel",
                "prefix": "/api/alerts",
                "responsibility": "Rich multimedia messaging with interactive buttons, maps, and shelter links via Twilio WhatsApp.",
                "status": "ONLINE"
            },
            {
                "id": "telegram_alert_system",
                "name": "Telegram Bot Alert Channel",
                "prefix": "/api/alerts",
                "responsibility": "Instant broadcast to community Telegram channels and direct subscriber chats.",
                "status": "ONLINE"
            },
            {
                "id": "ivrs_calling_system",
                "name": "IVRS Voice Calling Engine",
                "prefix": "/api/ivrs",
                "responsibility": "Automated voice emergency phone calls with text-to-speech TwiML synthesis.",
                "status": "ONLINE"
            },
            {
                "id": "evacuation_planning_engine",
                "name": "Evacuation Route Planning Engine",
                "prefix": "/api/evacuation",
                "responsibility": "Multi-objective Dijkstra/A* pathfinding avoiding submerged road networks to designated relief centers.",
                "status": "ONLINE"
            },
            {
                "id": "explainable_ai_module",
                "name": "Explainable AI (XAI) Attribution Engine",
                "prefix": "/api/xai",
                "responsibility": "SHAP TreeExplainer feature attributions, waterfall breakdowns, and operator headline narratives.",
                "status": "ONLINE"
            },
            {
                "id": "digital_twin_studio",
                "name": "Digital Twin Studio & Hydrological Sandbox",
                "prefix": "/api/digital-twin",
                "responsibility": "SCS-Curve Number runoff simulation, elevation DEM cross-sections, and interactive watershed twins.",
                "status": "ONLINE"
            },
            {
                "id": "flood_propagation_simulator",
                "name": "Flood Propagation & Inundation Simulator",
                "prefix": "/api/simulation",
                "responsibility": "Dynamic flood wave expansion, depth tiered classifications, and population/infrastructure exposure estimation.",
                "status": "ONLINE"
            }
        ]
    }


@router.post("/workflow/river-threshold-alert", summary="Workflow: Gauge Threshold Check & Alert Dispatch")
async def trigger_river_gauge_alert(request: RiverThresholdAlertRequest) -> Dict[str, Any]:
    """
    Evaluates water level for a river gauge against Warning and Danger thresholds.
    If breached, automatically triggers multi-channel emergency alert dispatch (SMS, WhatsApp, Telegram, IVRS).
    """
    orchestrator = get_platform_orchestrator()
    try:
        res = await orchestrator.trigger_gauge_threshold_alert(
            gauge_id=request.gauge_id,
            simulated_level_m=request.simulated_level_m,
            channels=request.channels,
            custom_recipient=request.custom_recipient,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Workflow failed: {e}")


@router.post("/workflow/predict-and-explain", summary="Workflow: ML Prediction with SHAP Feature Attribution")
def predict_and_explain(request: PredictAndExplainRequest) -> Dict[str, Any]:
    """
    Runs primary ML flood prediction engine (RandomForest/XGBoost/LightGBM) and
    attaches SHAP feature importance explanations. Maintains strict failure isolation:
    if XAI fails, prediction is returned safely without breaking.
    """
    orchestrator = get_platform_orchestrator()
    try:
        return orchestrator.predict_and_explain(
            gauge_id=request.gauge_id,
            rainfall_history_10d=request.rainfall_history_10d,
            onset_model=request.onset_model,
            active_model=request.active_model,
            explain=request.explain,
            region=request.region,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction workflow failed: {e}")


@router.post("/workflow/simulation-to-evacuation", summary="Workflow: Flood Simulation to Safe Evacuation Route")
def simulation_to_evacuation(request: SimulationEvacuationRequest) -> Dict[str, Any]:
    """
    Executes a flood propagation scenario, assesses submerged infrastructure,
    and automatically calculates optimal multi-factor evacuation path from origin to closest safe shelter.
    """
    orchestrator = get_platform_orchestrator()
    try:
        sim_req = SimulationRunRequest(
            scenario_type=request.scenario_type,
            simulation_period_hours=request.simulation_period_hours,
            rainfall_params=RainfallScenarioParams(
                rainfall_mm=request.rainfall_mm or 120.0,
                rainfall_duration_hours=4.0,
                spatial_distribution=SpatialDistribution.CONVECTIVE_CORE,
                catchment_id=request.catchment_id or "684",
                initial_soil_saturation_pct=85.0,
            ) if request.scenario_type == ScenarioType.RAINFALL else None,
        )

        return orchestrator.simulation_to_evacuation(
            origin_lat=request.origin_lat,
            origin_lng=request.origin_lng,
            simulation_request=sim_req,
            preferred_objective=request.preferred_objective,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Simulation-to-evacuation workflow failed: {e}")


@router.post("/workflow/end-to-end", summary="Workflow: Full Platform End-to-End Early Warning Lifecycle")
async def execute_end_to_end_lifecycle(request: EndToEndWorkflowRequest) -> Dict[str, Any]:
    """
    Executes complete 6-stage disaster response lifecycle:
    1. Gauge Telemetry Check
    2. ML Flood Prediction (RF/XGB)
    3. Explainable AI (SHAP)
    4. Flood Inundation Simulation
    5. Safe Evacuation Routing
    6. Central Multi-Channel Alert Dispatch (SMS + WhatsApp + Telegram + IVRS)
    """
    orchestrator = get_platform_orchestrator()
    rainfall_10d = request.rainfall_10d or [15.0, 18.0, 22.0, 35.0, 48.0, 72.0, 95.0, 120.0, 145.0, 160.0]
    try:
        return await orchestrator.execute_end_to_end(
            gauge_id=request.gauge_id,
            rainfall_10d=rainfall_10d,
            recipient_phone=request.recipient_phone,
            channels=request.channels,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"End-to-end lifecycle failed: {e}")
