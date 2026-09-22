"""Comprehensive Test Suite for PRAVAH Evacuation Planning & Safe Route Generation Engine."""
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.evacuation.models.route import (
    RouteRequest,
    RouteObjective,
    RoutingAlgorithm,
    SafetyClassification,
)
from src.evacuation.models.road import RoadStatus
from src.evacuation.models.shelter import ShelterStatus
from src.evacuation.road_network import RoadNetwork, build_default_road_network
from src.evacuation.algorithms.dijkstra import dijkstra_search
from src.evacuation.algorithms.astar import astar_search
from src.evacuation.route_scoring import compute_edge_cost, compute_route_breakdown, classify_route_safety
from src.evacuation.evacuation_manager import EvacuationManager
from src.evacuation.services.shelter_service import shelter_service
from src.evacuation.services.road_closure_service import road_closure_service
from src.evacuation.services.flood_risk_service import flood_risk_service


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestEvacuationAlgorithms:
    """Tests for Dijkstra and A* pathfinding algorithms."""

    def test_dijkstra_basic_path(self):
        net = RoadNetwork()
        net.add_node("A", "Node A", 18.50, 73.80)
        net.add_node("B", "Node B", 18.51, 73.81)
        net.add_node("C", "Node C", 18.52, 73.82)
        net.add_edge("AB", "A", "B", "Road AB", distance_km=2.0)
        net.add_edge("BC", "B", "C", "Road BC", distance_km=3.0)

        cost_fn = lambda e: e["distance_km"]
        res = dijkstra_search(net.adjacency, "A", "C", cost_fn)

        assert res is not None
        assert res["path"] == ["A", "B", "C"]
        assert res["total_distance_km"] == 5.0
        assert len(res["edges"]) == 2

    def test_astar_with_heuristic(self):
        net = RoadNetwork()
        net.add_node("A", "Node A", 18.50, 73.80)
        net.add_node("B", "Node B", 18.52, 73.80)
        net.add_node("C", "Node C", 18.54, 73.80)
        net.add_edge("AB", "A", "B", "Road AB", distance_km=2.2)
        net.add_edge("BC", "B", "C", "Road BC", distance_km=2.2)

        cost_fn = lambda e: e["distance_km"]
        node_coords = net.get_node_coordinates()
        res = astar_search(net.adjacency, node_coords, "A", "C", cost_fn)

        assert res is not None
        assert res["path"] == ["A", "B", "C"]
        assert res["total_distance_km"] == 4.4

    def test_closed_road_exclusion(self):
        """A closed road must be strictly excluded, forcing the alternative path."""
        net = RoadNetwork()
        net.add_node("S", "Start", 18.50, 73.80)
        net.add_node("M", "Middle Lowland", 18.51, 73.81)
        net.add_node("H", "High Ridge", 18.51, 73.79)
        net.add_node("D", "Destination", 18.52, 73.80)

        # Direct road through M is shorter but CLOSED due to flood
        net.add_edge("SM", "S", "M", "Direct Road", distance_km=1.0, status=RoadStatus.CLOSED)
        net.add_edge("MD", "M", "D", "Exit Road", distance_km=1.0)

        # Bypass road through H is longer but OPEN
        net.add_edge("SH", "S", "H", "Ridge Bypass 1", distance_km=3.0, status=RoadStatus.OPEN)
        net.add_edge("HD", "H", "D", "Ridge Bypass 2", distance_km=3.0, status=RoadStatus.OPEN)

        cost_fn = lambda e: compute_edge_cost(e, RouteObjective.FASTEST)
        res = dijkstra_search(net.adjacency, "S", "D", cost_fn)

        assert res is not None
        assert res["path"] == ["S", "H", "D"]
        assert res["total_distance_km"] == 6.0
        assert res["closures_avoided"] >= 1

    def test_flood_risk_influences_route_selection(self):
        """LOWEST_RISK mode must choose the safer, longer route over the hazardous shorter one."""
        net = RoadNetwork()
        net.add_node("S", "Start", 18.50, 73.80)
        net.add_node("L", "Lowland Hazard", 18.51, 73.81)
        net.add_node("R", "Safe Ridge", 18.51, 73.79)
        net.add_node("D", "Shelter", 18.52, 73.80)

        # Short path via L: 2 km, moderate flood risk (0.40)
        net.add_edge("SL", "S", "L", "Lowland Valley 1", distance_km=1.0, flood_risk=0.40)
        net.add_edge("LD", "L", "D", "Lowland Valley 2", distance_km=1.0, flood_risk=0.40)

        # Longer path via R: 8 km, low flood risk (0.02)
        net.add_edge("SR", "S", "R", "Safe Elevated Way 1", distance_km=4.0, flood_risk=0.02)
        net.add_edge("RD", "R", "D", "Safe Elevated Way 2", distance_km=4.0, flood_risk=0.02)

        # 1. LOWEST_RISK should take the safe route via R
        cost_fn_risk = lambda e: compute_edge_cost(e, RouteObjective.LOWEST_RISK)
        res_risk = dijkstra_search(net.adjacency, "S", "D", cost_fn_risk)
        assert res_risk is not None
        assert res_risk["path"] == ["S", "R", "D"]
        assert res_risk["avg_risk"] < 0.10

        # 2. FASTEST should take the short route via L
        cost_fn_fast = lambda e: compute_edge_cost(e, RouteObjective.FASTEST)
        res_fast = dijkstra_search(net.adjacency, "S", "D", cost_fn_fast)
        assert res_fast is not None
        assert res_fast["path"] == ["S", "L", "D"]

    def test_partially_blocked_road_penalties(self):
        """A PARTIALLY_BLOCKED road incurs time and risk penalties."""
        open_edge = {"distance_km": 5.0, "base_speed_kmh": 50.0, "flood_risk": 0.1, "status": "OPEN"}
        blocked_edge = {"distance_km": 5.0, "base_speed_kmh": 50.0, "flood_risk": 0.1, "status": "PARTIALLY_BLOCKED"}

        cost_open = compute_edge_cost(open_edge, RouteObjective.BALANCED)
        cost_blocked = compute_edge_cost(blocked_edge, RouteObjective.BALANCED)

        # Partial block must significantly increase routing cost
        assert cost_blocked > cost_open + 8.0


class TestEvacuationManager:
    """Tests for the high-level EvacuationManager orchestrator."""

    def test_plan_evacuation_pune_success(self):
        mgr = EvacuationManager()
        req = RouteRequest(
            latitude=18.5204,
            longitude=73.8567,
            objective=RouteObjective.BALANCED,
            algorithm=RoutingAlgorithm.ASTAR,
        )
        plan = mgr.plan_evacuation(req)

        assert plan.status == "success"
        assert plan.primary_route is not None
        assert plan.primary_route.distance_km > 0
        assert plan.primary_route.estimated_time_minutes > 0
        assert plan.primary_route.destination["name"] is not None
        assert len(plan.primary_route.polyline) >= 2
        assert len(plan.alternative_routes) >= 1

    def test_plan_evacuation_fastest_vs_lowest_risk(self):
        mgr = EvacuationManager()
        req_fast = RouteRequest(
            latitude=18.5204,
            longitude=73.8567,
            objective=RouteObjective.FASTEST,
            algorithm=RoutingAlgorithm.DIJKSTRA,
        )
        plan_fast = mgr.plan_evacuation(req_fast)

        req_risk = RouteRequest(
            latitude=18.5204,
            longitude=73.8567,
            objective=RouteObjective.LOWEST_RISK,
            algorithm=RoutingAlgorithm.ASTAR,
        )
        plan_risk = mgr.plan_evacuation(req_risk)

        assert plan_fast.status == "success"
        assert plan_risk.status == "success"
        assert plan_fast.primary_route.objective == RouteObjective.FASTEST
        assert plan_risk.primary_route.objective == RouteObjective.LOWEST_RISK

    def test_shelter_exclusion_when_full(self):
        """A shelter marked FULL must not be selected as the destination."""
        mgr = EvacuationManager()
        # Mark SH-1 (Shivaji Nagar) as FULL
        shelter_service.update_shelter_status("SH-1", ShelterStatus.FULL, occupancy=650)

        req = RouteRequest(
            latitude=18.5204,
            longitude=73.8567,
            destination_shelter_id="SH-1",
        )
        plan = mgr.plan_evacuation(req)

        assert plan.status == "no_safe_route"
        assert "FULL" in plan.message

        # Restore SH-1 status
        shelter_service.update_shelter_status("SH-1", ShelterStatus.AVAILABLE, occupancy=260)

    def test_no_safe_route_available_when_completely_blocked(self):
        """When an origin node is isolated by closures, returns NO_SAFE_ROUTE_AVAILABLE."""
        mgr = EvacuationManager()
        # Create an isolated mock network
        isolated_net = RoadNetwork()
        isolated_net.add_node("ISOLATED_ORIGIN", "Trapped Island", 18.50, 73.80)
        isolated_net.add_node("SAFE_SHELTER", "Safe High Ground", 18.55, 73.85, "shelter", "SH-1")
        isolated_net.add_edge("BLOCKED_EXIT", "ISOLATED_ORIGIN", "SAFE_SHELTER", "Only Road", distance_km=5.0, status=RoadStatus.CLOSED)

        mgr._network = isolated_net
        req = RouteRequest(
            latitude=18.50,
            longitude=73.80,
            objective=RouteObjective.FASTEST,
        )
        plan = mgr.plan_evacuation(req, refresh_hazards=False)

        assert plan.status == "no_safe_route"
        assert "NO_SAFE_ROUTE_AVAILABLE" in plan.message


class TestEvacuationAPIs:
    """Tests for REST endpoints under /api/evacuation/."""

    def test_post_evacuation_route(self, client):
        payload = {
            "latitude": 18.5204,
            "longitude": 73.8567,
            "objective": "FASTEST",
            "algorithm": "ASTAR",
            "travel_mode": "VEHICLE",
        }
        res = client.post("/api/evacuation/route", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "primary_route" in data
        assert data["primary_route"]["distance_km"] > 0
        assert data["primary_route"]["safety_classification"] in [
            "LOW_RISK", "MODERATE_RISK", "HIGH_RISK", "UNSAFE"
        ]

    def test_get_evacuation_shelters(self, client):
        res = client.get("/api/evacuation/shelters")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 10
        assert any(s["id"] == "SH-1" for s in data)

    def test_get_single_shelter(self, client):
        res = client.get("/api/evacuation/shelters/SH-1")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "SH-1"
        assert data["name"] == "Shivaji Nagar Elevated Disaster Shelter"

    def test_patch_shelter_status(self, client):
        update = {"status": "NEAR_CAPACITY", "current_occupancy": 580}
        res = client.patch("/api/evacuation/shelters/SH-1", json=update)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "NEAR_CAPACITY"
        assert data["current_occupancy"] == 580

        # Restore
        client.patch("/api/evacuation/shelters/SH-1", json={"status": "AVAILABLE", "current_occupancy": 260})

    def test_get_risk_zones_geojson(self, client):
        res = client.get("/api/evacuation/risk-zones")
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) >= 4

    def test_road_closures_lifecycle(self, client):
        # 1. List closures
        res = client.get("/api/evacuation/road-closures")
        assert res.status_code == 200
        closures = res.json()
        assert len(closures) >= 2

        # 2. Add temporary closure
        new_closure = {
            "road_id": "TEST-BLOCK-99",
            "name": "Test Flooded Causeway",
            "status": "CLOSED",
            "cause": "Flash flood test inundation",
        }
        res_post = client.post("/api/evacuation/road-closures", json=new_closure)
        assert res_post.status_code == 200

        # 3. Verify presence
        res_list = client.get("/api/evacuation/road-closures")
        assert any(c["road_id"] == "TEST-BLOCK-99" for c in res_list.json())

        # 4. Remove closure
        res_del = client.delete("/api/evacuation/road-closures/TEST-BLOCK-99")
        assert res_del.status_code == 200

    def test_legacy_evacuation_endpoint_preserved(self, client):
        """Strict backward compatibility: /api/evacuation-route must work identically."""
        res = client.get("/api/evacuation-route?lat=18.5204&lng=73.8567")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "nearest_camp" in data
        assert "primary_evacuation_route" in data
        assert "polyline" in data["primary_evacuation_route"]
