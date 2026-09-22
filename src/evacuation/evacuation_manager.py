"""Primary Orchestrator for PRAVAH Evacuation Planning and Safe Routing."""
import math
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from src.evacuation.models.route import (
    RouteRequest,
    EvacuationRoute,
    EvacuationPlanResponse,
    RouteObjective,
    RoutingAlgorithm,
    SafetyClassification,
    Waypoint,
)
from src.evacuation.models.shelter import Shelter, ShelterStatus
from src.evacuation.road_network import RoadNetwork, build_default_road_network
from src.evacuation.route_engine import RouteEngine
from src.evacuation.risk_engine import risk_engine
from src.evacuation.route_scoring import compute_route_breakdown, classify_route_safety
from src.evacuation.services.shelter_service import shelter_service
from src.evacuation.services.road_closure_service import road_closure_service
from src.evacuation.services.flood_risk_service import flood_risk_service
from src.evacuation.services.route_service import save_evacuation_route
from src.evacuation.utils.geo_utils import haversine_distance


class EvacuationManager:
    """
    Central orchestration service for evacuation planning:
    Processes flood hazard layers, road closures, and shelter availability to
    generate optimal, safety-scored evacuation routes using Dijkstra and A*.
    """

    def __init__(self):
        self._network: RoadNetwork = build_default_road_network()
        self._route_engine = RouteEngine()
        # Synchronize dynamic risks and closures onto the graph
        risk_engine.apply_hazards_to_network(self._network)

    def reload_network(self) -> RoadNetwork:
        """Re-initializes network with latest active hazards and closures."""
        self._network = build_default_road_network()
        risk_engine.apply_hazards_to_network(self._network)
        return self._network

    def plan_evacuation(
        self, request: RouteRequest, refresh_hazards: bool = True
    ) -> EvacuationPlanResponse:
        """
        Computes safe evacuation routes from origin to suitable relief shelter(s).
        Returns primary route and alternative choices (Fastest, Lowest-Risk, Balanced).
        """
        # Ensure latest hazard state is reflected on graph
        if refresh_hazards:
            risk_engine.apply_hazards_to_network(self._network)

        origin_lat = request.latitude
        origin_lng = request.longitude
        is_ne = (23.5 <= origin_lat <= 29.5 and 88.5 <= origin_lng <= 98.0)
        region = "Northeast" if is_ne else "Maharashtra"

        # 1. Locate closest accessible network entry node
        start_node = self._network.find_nearest_node(origin_lat, origin_lng, max_dist_km=250.0)
        if not start_node:
            return EvacuationPlanResponse(
                status="no_safe_route",
                message=(
                    "No suitable evacuation road node is accessible from the selected GPS location. "
                    "Please move towards higher elevation and follow directives from local emergency services."
                ),
                available_shelters_count=len(shelter_service.get_available_shelters(region)),
                active_closures_count=len(road_closure_service.get_all_closures()),
            )

        # 2. Select Candidate Target Shelters
        candidate_shelters: List[Shelter] = []
        if request.destination_shelter_id:
            s = shelter_service.get_shelter(request.destination_shelter_id)
            if s and s.is_accepting_evacuees:
                candidate_shelters.append(s)
            elif s:
                # Specified shelter is full or closed
                return EvacuationPlanResponse(
                    status="no_safe_route",
                    message=f"Requested shelter '{s.name}' is currently {s.status.value} and cannot accept evacuees.",
                    available_shelters_count=len(shelter_service.get_available_shelters(region)),
                    active_closures_count=len(road_closure_service.get_all_closures()),
                )

        if not candidate_shelters:
            # Query all available shelters in region
            candidate_shelters = shelter_service.get_available_shelters(region)
            if not candidate_shelters:
                candidate_shelters = shelter_service.get_available_shelters()

        if not candidate_shelters:
            return EvacuationPlanResponse(
                status="no_safe_route",
                message="All designated relief shelters in this regional sector are currently FULL or CLOSED.",
                available_shelters_count=0,
                active_closures_count=len(road_closure_service.get_all_closures()),
            )

        # 3. Find corresponding network nodes for shelters
        shelter_node_map: Dict[str, Tuple[str, Shelter]] = {}
        for s in candidate_shelters:
            # Check if there is an explicit node for this shelter
            matched_node = None
            for nid, n in self._network.nodes.items():
                if n.get("shelter_id") == s.id:
                    matched_node = nid
                    break
            if not matched_node:
                matched_node = self._network.find_nearest_node(s.latitude, s.longitude, max_dist_km=2.5)
            if matched_node and (matched_node != start_node or self._network.nodes[matched_node].get("shelter_id") == s.id):
                shelter_node_map[matched_node] = (matched_node, s)

        # 4. Compute Routes for Multiple Objectives
        routes_by_obj: Dict[RouteObjective, Optional[EvacuationRoute]] = {}
        objectives = [
            request.objective,
            RouteObjective.FASTEST if request.objective != RouteObjective.FASTEST else RouteObjective.LOWEST_RISK,
            RouteObjective.BALANCED if request.objective not in (RouteObjective.BALANCED, RouteObjective.NEAREST_SHELTER) else RouteObjective.LOWEST_RISK,
        ]
        # De-duplicate objectives list preserving order
        seen_objs = set()
        clean_objectives = []
        for obj in objectives:
            if obj not in seen_objs:
                seen_objs.add(obj)
                clean_objectives.append(obj)

        for obj in clean_objectives:
            best_route = self._find_best_route_for_objective(
                start_node=start_node,
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                shelter_node_map=shelter_node_map,
                objective=obj,
                algorithm=request.algorithm,
                travel_mode=request.travel_mode,
            )
            if best_route:
                routes_by_obj[obj] = best_route

        if not routes_by_obj:
            return EvacuationPlanResponse(
                status="no_safe_route",
                message=(
                    "NO_SAFE_ROUTE_AVAILABLE: All access corridors to regional relief shelters are currently "
                    "inundated, completely blocked by debris, or impassable. "
                    "Remain at your current high-ground refuge and await NDRF/SDRF rescue deployment."
                ),
                available_shelters_count=len(candidate_shelters),
                active_closures_count=len(road_closure_service.get_all_closures()),
            )

        # Primary route corresponds to the requested objective
        primary = routes_by_obj.get(request.objective) or next(iter(routes_by_obj.values()))

        # Collect alternatives
        alternatives = [r for obj, r in routes_by_obj.items() if r and r.route_id != primary.route_id]

        # Persist primary route in SQLite audit log
        try:
            save_evacuation_route(primary)
        except Exception:
            pass

        return EvacuationPlanResponse(
            status="success",
            message=f"Safe evacuation route generated to {primary.destination.get('name', 'Relief Shelter')} ({primary.safety_classification.value}).",
            primary_route=primary,
            alternative_routes=alternatives,
            available_shelters_count=len(candidate_shelters),
            active_closures_count=len(road_closure_service.get_all_closures()),
        )

    def _find_best_route_for_objective(
        self,
        start_node: str,
        origin_lat: float,
        origin_lng: float,
        shelter_node_map: Dict[str, Tuple[str, Shelter]],
        objective: RouteObjective,
        algorithm: RoutingAlgorithm,
        travel_mode: str,
    ) -> Optional[EvacuationRoute]:
        """Evaluates paths across all candidate shelter targets and selects optimal for objective."""
        best_plan = None
        min_metric = math.inf

        for target_node, (_, shelter) in shelter_node_map.items():
            if target_node == start_node:
                continue

            res = self._route_engine.compute_path(
                network=self._network,
                start_node=start_node,
                target_node=target_node,
                objective=objective,
                algorithm=algorithm,
                travel_mode=travel_mode,
            )
            if not res or not res["path"] or not res["edges"]:
                continue

            edges = res["edges"]
            breakdown = compute_route_breakdown(edges, travel_mode=travel_mode)

            # Metric used for ranking
            if objective == RouteObjective.FASTEST:
                metric = breakdown["total_time_minutes"]
            elif objective == RouteObjective.LOWEST_RISK:
                metric = breakdown["risk_score"] * 100.0 + (breakdown["total_time_minutes"] * 0.1)
            elif objective == RouteObjective.NEAREST_SHELTER:
                metric = breakdown["distance_km"]
            else:  # BALANCED
                metric = breakdown["total_time_minutes"] + (breakdown["risk_score"] * 30.0)

            if metric < min_metric:
                min_metric = metric
                best_plan = (res, breakdown, shelter)

        if not best_plan:
            return None

        res, breakdown, shelter = best_plan
        edges = res["edges"]

        # Build detailed polyline and waypoints
        polyline: List[List[float]] = [[origin_lat, origin_lng]]
        waypoints: List[Waypoint] = []
        cum_dist = 0.0
        cum_time = 0.0

        for idx, e in enumerate(edges):
            coords = e.get("coordinates", [])
            for pt in coords:
                polyline.append(pt)

            to_node_data = self._network.nodes.get(e["to_node"], {})
            cum_dist += e.get("distance_km", 0.0)
            seg_time = (e.get("distance_km", 0.0) / max(1.0, e.get("base_speed_kmh", 40.0))) * 60.0
            cum_time += seg_time

            waypoints.append(
                Waypoint(
                    node_id=e["to_node"],
                    name=to_node_data.get("name", f"Junction {e['to_node']}"),
                    latitude=to_node_data.get("latitude", 0.0),
                    longitude=to_node_data.get("longitude", 0.0),
                    cumulative_distance_km=round(cum_dist, 2),
                    cumulative_time_mins=round(cum_time, 1),
                    risk_score=e.get("flood_risk", 0.0),
                )
            )

        # Add destination shelter coordinate to end of polyline
        polyline.append([shelter.latitude, shelter.longitude])

        route_id = f"EVAC-{str(uuid.uuid4())[:8].upper()}"

        return EvacuationRoute(
            route_id=route_id,
            origin={"latitude": origin_lat, "longitude": origin_lng},
            destination={
                "shelter_id": shelter.id,
                "name": shelter.name,
                "latitude": shelter.latitude,
                "longitude": shelter.longitude,
                "capacity": shelter.capacity,
                "current_occupancy": shelter.current_occupancy,
                "status": shelter.status.value,
                "contact": shelter.contact,
                "accessibility": shelter.accessibility_notes,
            },
            distance_km=breakdown["distance_km"],
            estimated_time_minutes=breakdown["total_time_minutes"],
            base_time_minutes=breakdown["base_time_minutes"],
            flood_delay_minutes=breakdown["flood_delay_minutes"],
            road_delay_minutes=breakdown["road_delay_minutes"],
            risk_score=breakdown["risk_score"],
            safety_classification=breakdown["safety_classification"],
            algorithm_used=algorithm,
            objective=objective,
            polyline=polyline,
            waypoints=waypoints,
            road_closures_avoided=res.get("closures_avoided", 0),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


evacuation_manager = EvacuationManager()
