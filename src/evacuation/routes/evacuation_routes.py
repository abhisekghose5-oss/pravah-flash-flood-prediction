"""FastAPI router for PRAVAH Evacuation Planning Engine."""
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.evacuation.models.route import (
    RouteRequest,
    EvacuationPlanResponse,
    EvacuationRoute,
    RouteObjective,
    RoutingAlgorithm,
)
from src.evacuation.models.shelter import Shelter, ShelterStatus
from src.evacuation.models.road import RoadStatus
from src.evacuation.evacuation_manager import evacuation_manager
from src.evacuation.services.shelter_service import shelter_service
from src.evacuation.services.flood_risk_service import flood_risk_service
from src.evacuation.services.road_closure_service import road_closure_service
from src.evacuation.services.route_service import (
    get_recent_evacuation_routes,
    get_route_by_code,
)

router = APIRouter(prefix="/api/evacuation", tags=["Evacuation Engine"])


class ShelterStatusUpdate(BaseModel):
    status: ShelterStatus
    current_occupancy: Optional[int] = None


class RoadClosureCreate(BaseModel):
    road_id: str = Field(..., description="Unique road code, e.g. 'RD-NH48-BLOCK'")
    name: str = Field(..., description="Highway name")
    status: RoadStatus = Field(RoadStatus.CLOSED)
    cause: str = Field(..., description="Reason for closure")
    coordinates: Optional[List[List[float]]] = None


@router.post(
    "/route",
    response_model=EvacuationPlanResponse,
    summary="Compute safe multi-factor evacuation routes",
)
def calculate_evacuation_route(request: RouteRequest) -> EvacuationPlanResponse:
    """
    Computes optimal, safe evacuation paths from user coordinates to suitable relief shelters.
    Evaluates flood hazard exposure, prunes closed roads, and applies transit delay penalties.
    Returns primary recommended path alongside alternative options (Fastest, Lowest-Risk, Balanced).
    """
    try:
        return evacuation_manager.plan_evacuation(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evacuation planning calculation error: {str(exc)}",
        )


@router.get(
    "/shelters",
    response_model=List[Shelter],
    summary="List all disaster relief shelters and live capacity",
)
def list_evacuation_shelters(
    region: Optional[str] = Query(None, description="Filter: 'Maharashtra' or 'Northeast'"),
    available_only: bool = Query(False, description="Filter for accepting shelters only"),
) -> List[Shelter]:
    """Returns directory of designated disaster relief shelters with operational capacity."""
    if available_only:
        return shelter_service.get_available_shelters(region=region)
    return shelter_service.get_all_shelters(region=region)


@router.get(
    "/shelters/{shelter_id}",
    response_model=Shelter,
    summary="Get single shelter details",
)
def get_shelter_detail(shelter_id: str) -> Shelter:
    """Retrieves operational details for a specific shelter."""
    s = shelter_service.get_shelter(shelter_id)
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shelter '{shelter_id}' not found.",
        )
    return s


@router.patch(
    "/shelters/{shelter_id}",
    response_model=Shelter,
    summary="Update shelter capacity or status",
)
def update_shelter_status_endpoint(
    shelter_id: str, update: ShelterStatusUpdate
) -> Shelter:
    """Updates operational state (AVAILABLE, NEAR_CAPACITY, FULL, CLOSED) and occupancy."""
    s = shelter_service.update_shelter_status(
        shelter_id=shelter_id,
        status=update.status,
        occupancy=update.current_occupancy,
    )
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shelter '{shelter_id}' not found.",
        )
    return s


@router.get(
    "/risk-zones",
    summary="Get active flood risk zones as GeoJSON FeatureCollection",
)
def get_risk_zones() -> Dict[str, Any]:
    """Returns spatial GeoJSON FeatureCollection of river basin flood risk polygons."""
    return flood_risk_service.get_risk_zones_geojson()


@router.get(
    "/road-closures",
    summary="List all active road closures and partial obstructions",
)
def get_road_closures() -> List[Dict[str, Any]]:
    """Returns active road segments that are completely closed or partially obstructed."""
    return road_closure_service.get_all_closures()


@router.post(
    "/road-closures",
    summary="Register a new road closure or obstruction",
)
def add_road_closure(closure: RoadClosureCreate) -> Dict[str, Any]:
    """Adds or updates a road closure, instantly updating pathfinding graphs."""
    res = road_closure_service.set_closure(
        road_id=closure.road_id,
        name=closure.name,
        status=closure.status,
        cause=closure.cause,
        coordinates=closure.coordinates,
    )
    evacuation_manager.reload_network()
    return {"status": "success", "closure": res}


@router.delete(
    "/road-closures/{road_id}",
    summary="Reopen or clear a road closure",
)
def remove_road_closure(road_id: str) -> Dict[str, Any]:
    """Removes a road closure and restores edge traversal in the graph."""
    success = road_closure_service.remove_closure(road_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Road closure '{road_id}' not found.",
        )
    evacuation_manager.reload_network()
    return {"status": "success", "message": f"Road '{road_id}' cleared and reopened."}


@router.get(
    "/routes",
    summary="List recently generated evacuation routes audit history",
)
def list_recent_routes(limit: int = Query(25, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Fetches recent evacuation plans generated by dispatchers and citizens."""
    return get_recent_evacuation_routes(limit=limit)


@router.get(
    "/routes/{route_id}",
    summary="Retrieve single evacuation route by ID",
)
def get_route_by_id(route_id: str) -> Dict[str, Any]:
    """Retrieves detailed waypoint and geometry metadata for an evacuation route."""
    r = get_route_by_code(route_id)
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evacuation route '{route_id}' not found.",
        )
    return r


@router.get(
    "/network",
    summary="Get summary of road network topology",
)
def get_network_summary() -> Dict[str, Any]:
    """Returns summary of graph nodes and active road segments."""
    net = evacuation_manager._network
    return {
        "nodes_count": len(net.nodes),
        "edges_count": len(net.get_all_edges()),
        "active_closures_count": len(road_closure_service.get_all_closures()),
        "shelters_count": len(shelter_service.get_all_shelters()),
    }
