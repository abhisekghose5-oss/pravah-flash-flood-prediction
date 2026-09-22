"""
PRAVAH Digital Twin — REST API Router.
Mounted under /api/digital-twin to provide endpoints for hydrological simulation,
watershed querying, terrain elevation extraction, river basins, and visualization layers.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from src.digital_twin.digital_twin_manager import DigitalTwinManager
from src.digital_twin.models.watershed import (
    WatershedListResponse,
    WatershedProperties,
)
from src.digital_twin.models.terrain import TerrainModelOutput
from src.digital_twin.models.river_basin import RiverBasinSummary
from src.digital_twin.models.simulation import (
    SimulationRequest,
    SimulationResult,
    AntecedentMoistureCondition,
    SimulationMode,
)

logger = logging.getLogger("pravah.digital_twin.routes")

router = APIRouter(
    prefix="/api/digital-twin",
    tags=["Digital Twin & Hydrological Simulation"],
)


@router.get("/status", summary="Digital Twin System Health & Status")
async def get_status() -> Dict[str, Any]:
    """Return health status and capabilities of the Digital Twin engine."""
    manager = DigitalTwinManager.get_instance()
    all_ws = manager.geojson_service.get_all_watersheds()
    basins = manager.geojson_service.get_river_basins_summary()

    return {
        "status": "online",
        "service": "PRAVAH Digital Twin Studio",
        "version": "2.0.0",
        "capabilities": [
            "watershed_modeling",
            "terrain_dem_processing",
            "river_basin_network",
            "scs_cn_runoff_simulation",
            "water_accumulation_routing",
            "dynamic_flow_particles",
        ],
        "monitored_watersheds_count": len(all_ws),
        "river_basins_count": len(basins),
        "regions_supported": ["Maharashtra Western Ghats", "Northeast India (Assam)"],
    }


@router.get("/watersheds", response_model=WatershedListResponse, summary="List All Monitored Watersheds")
async def get_watersheds() -> WatershedListResponse:
    """Retrieve all monitored catchments with metadata and GeoJSON boundaries."""
    try:
        manager = DigitalTwinManager.get_instance()
        return manager.get_all_watersheds()
    except Exception as exc:
        logger.error("Failed to retrieve watersheds: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load watershed catalog",
        )


@router.get("/watersheds/{watershed_id}", summary="Get Specific Watershed Details")
async def get_watershed_detail(watershed_id: str) -> Dict[str, Any]:
    """Retrieve complete metadata, boundary polygon, and sub-catchments for a watershed."""
    manager = DigitalTwinManager.get_instance()
    ws = manager.get_watershed(watershed_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watershed '{watershed_id}' not found in Digital Twin database",
        )
    return ws.model_dump()


@router.get("/terrain", response_model=TerrainModelOutput, summary="Get DEM & Terrain Elevation Model")
async def get_terrain(
    watershed_id: str = Query(..., description="Target watershed identifier e.g. INDOFLOODS-gauge-602")
) -> TerrainModelOutput:
    """Derive elevation contours, slope gradients, and aspect distribution for a watershed."""
    manager = DigitalTwinManager.get_instance()
    terrain = manager.get_terrain_model(watershed_id)
    if not terrain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Terrain data unavailable for watershed '{watershed_id}'",
        )
    return terrain


@router.get("/river-basins", response_model=List[RiverBasinSummary], summary="List Monitored River Basins")
async def get_river_basins() -> List[RiverBasinSummary]:
    """Retrieve aggregated river basin summaries and active monitoring stations."""
    manager = DigitalTwinManager.get_instance()
    return manager.get_river_basins()


@router.get("/river-basins/{watershed_id}/network", summary="Get River Channel Network for Watershed")
async def get_river_network(watershed_id: str) -> Dict[str, Any]:
    """Retrieve GeoJSON LineString reaches and Strahler stream orders."""
    manager = DigitalTwinManager.get_instance()
    return manager.get_river_network(watershed_id)


@router.get("/scenarios", summary="Get Preset Benchmark Scenarios")
async def get_scenarios() -> List[Dict[str, Any]]:
    """Retrieve library of pre-configured historic flood and cloudburst scenarios."""
    manager = DigitalTwinManager.get_instance()
    return manager.get_scenarios()


@router.get("/layers", summary="Get Visualization Layer Manifest")
async def get_layer_manifest() -> Dict[str, Any]:
    """Return available map visualization layers and styling metadata."""
    manager = DigitalTwinManager.get_instance()
    return manager.get_layer_manifest()


@router.post("/simulate", response_model=SimulationResult, summary="Execute Hydrological Simulation")
async def run_simulation(request: SimulationRequest) -> SimulationResult:
    """
    Execute coupled physical rainfall-runoff and water accumulation simulation.
    Uses the SCS Curve Number method calibrated against catchment soil and relief.
    """
    try:
        manager = DigitalTwinManager.get_instance()
        return manager.run_simulation(request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error("Simulation execution failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hydrological simulation engine encountered an internal calculation error",
        )


@router.get("/runoff", summary="Query Runoff Model Parameters")
async def get_runoff_info(
    watershed_id: str = Query(..., description="Target watershed ID"),
    rainfall_mm: float = Query(100.0, ge=1.0, le=1000.0),
    duration_hours: float = Query(3.0, ge=0.5, le=72.0),
    amc: AntecedentMoistureCondition = Query(AntecedentMoistureCondition.AMC_II),
) -> Dict[str, Any]:
    """Calculate and inspect SCS-CN runoff metrics without full spatial rendering."""
    manager = DigitalTwinManager.get_instance()
    ws = manager.get_watershed(watershed_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watershed '{watershed_id}' not found",
        )
    runoff = manager.simulation_engine.compute_scs_runoff(
        watershed=ws,
        rainfall_mm=rainfall_mm,
        duration_hours=duration_hours,
        amc=amc,
    )
    return {
        "watershed_id": ws.id,
        "station_name": ws.properties.station_name,
        "river_name": ws.properties.river_name,
        "runoff_metrics": runoff.model_dump(),
    }


@router.get("/accumulation", summary="Query Water Accumulation Zones")
async def get_accumulation_info(
    watershed_id: str = Query(..., description="Target watershed ID"),
    rainfall_mm: float = Query(100.0, ge=1.0, le=1000.0),
) -> Dict[str, Any]:
    """Retrieve estimated water accumulation zones for a given precipitation amount."""
    manager = DigitalTwinManager.get_instance()
    ws = manager.get_watershed(watershed_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watershed '{watershed_id}' not found",
        )
    zones, geojson_fc = manager.raster_service.generate_accumulation_layers(
        watershed=ws,
        direct_runoff_depth_mm=rainfall_mm * 0.65,
        rainfall_intensity_mmhr=rainfall_mm / 3.0,
    )
    return {
        "watershed_id": ws.id,
        "zones": [z.model_dump() for z in zones],
        "geojson_layer": geojson_fc,
    }
