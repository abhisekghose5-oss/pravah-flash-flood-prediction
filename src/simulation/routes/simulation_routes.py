"""
PRAVAH Flood Propagation — REST API Router.
Mounted under /api/simulation to provide endpoints for multi-scenario flood propagation,
time-step advancement, inundation spatial mapping, population exposure, and infrastructure impacts.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from src.simulation.models.scenario import ScenarioTemplate
from src.simulation.models.simulation import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationTimelineResponse,
    SimulationHistoryItem,
)
from src.simulation.simulation_manager import get_simulation_manager

logger = logging.getLogger("pravah.simulation.routes")

router = APIRouter(
    prefix="/api/simulation",
    tags=["Flood Propagation & Inundation Simulation"],
)


@router.get("/status", summary="Simulation Engine Operational Status")
async def get_simulation_status() -> Dict[str, Any]:
    """
    Diagnostic status and telemetry capabilities of the PRAVAH Flood Propagation Engine.
    """
    manager = get_simulation_manager()
    return manager.get_status()


@router.get("/scenarios", response_model=List[ScenarioTemplate], summary="List Benchmark Scenario Templates")
async def get_scenarios() -> List[ScenarioTemplate]:
    """
    Retrieve pre-configured benchmark scenarios (Rainfall Deluge, Koyna Dam Release, Savitri River Overflow).
    """
    manager = get_simulation_manager()
    return manager.get_scenario_templates()


@router.get("/history", response_model=List[SimulationHistoryItem], summary="Simulation Execution History")
async def get_history(limit: int = Query(20, ge=1, le=100)) -> List[SimulationHistoryItem]:
    """
    Retrieve recent simulation executions with high-level summary metrics.
    """
    manager = get_simulation_manager()
    return manager.list_history(limit=limit)


@router.post("/run", response_model=SimulationRunResponse, summary="Execute Flood Propagation Simulation")
async def run_simulation(request: SimulationRunRequest) -> SimulationRunResponse:
    """
    Trigger dynamic, multi-period flood propagation across 1h, 6h, 12h, 24h, or 48h.
    Computes time-based inundation polygons, depth distribution, demographic exposure, and infrastructure impact.
    """
    try:
        manager = get_simulation_manager()
        response = manager.run_simulation(request)
        return response
    except ValueError as val_err:
        logger.warning("Simulation validation error: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.exception("Error executing simulation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation computational failure: {str(exc)}",
        )


@router.get("/{simulation_id}", response_model=SimulationRunResponse, summary="Get Simulation Results by ID")
async def get_simulation_by_id(simulation_id: str) -> SimulationRunResponse:
    """
    Retrieve complete results for a previously executed simulation run.
    """
    manager = get_simulation_manager()
    sim = manager.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found in cache",
        )
    return sim


@router.get("/{simulation_id}/inundation", summary="Get Spatial Inundation and Depth Layers")
async def get_simulation_inundation(
    simulation_id: str,
    time_step_hour: Optional[float] = Query(None, description="Optional elapsed hour (e.g. 1.0, 6.0, 12.0)"),
) -> Dict[str, Any]:
    """
    Retrieve GeoJSON polygons and depth classification stats, optionally at a specific elapsed time step.
    """
    manager = get_simulation_manager()
    data = manager.get_simulation_inundation(simulation_id, time_step_hour=time_step_hour)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )
    return data


@router.get("/{simulation_id}/population-impact", summary="Get Demographic Exposure Assessment")
async def get_simulation_population_impact(
    simulation_id: str,
    time_step_hour: Optional[float] = Query(None, description="Optional elapsed hour"),
) -> Dict[str, Any]:
    """
    Retrieve resident population exposure, high-risk counts, and evacuation urgency.
    """
    manager = get_simulation_manager()
    data = manager.get_population_impact(simulation_id, time_step_hour=time_step_hour)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )
    return data


@router.get("/{simulation_id}/infrastructure-impact", summary="Get Lifeline Infrastructure Impact")
async def get_simulation_infrastructure_impact(
    simulation_id: str,
    time_step_hour: Optional[float] = Query(None, description="Optional elapsed hour"),
) -> Dict[str, Any]:
    """
    Retrieve road submergence, bridge outages, hospital and school vulnerabilities.
    """
    manager = get_simulation_manager()
    data = manager.get_infrastructure_impact(simulation_id, time_step_hour=time_step_hour)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )
    return data


@router.get("/{simulation_id}/timeline", response_model=SimulationTimelineResponse, summary="Get Lightweight Chart Timeline")
async def get_simulation_timeline(simulation_id: str) -> SimulationTimelineResponse:
    """
    Retrieve compact growth and demographic time-series data for front-end charting.
    """
    manager = get_simulation_manager()
    data = manager.get_timeline(simulation_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )
    return data


@router.delete("/{simulation_id}", summary="Cancel Simulation Run")
async def cancel_simulation(simulation_id: str) -> Dict[str, Any]:
    """
    Cancel an active simulation run.
    """
    manager = get_simulation_manager()
    success = manager.cancel_simulation(simulation_id)
    return {
        "simulation_id": simulation_id,
        "cancelled": success,
        "message": "Simulation cancelled" if success else "Simulation not active or not found",
    }
