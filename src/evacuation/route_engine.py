"""Pathfinding Route Engine implementing the Strategy Pattern."""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from src.evacuation.road_network import RoadNetwork
from src.evacuation.models.route import RouteObjective, RoutingAlgorithm
from src.evacuation.route_scoring import compute_edge_cost
from src.evacuation.algorithms.dijkstra import dijkstra_search
from src.evacuation.algorithms.astar import astar_search


class RouteStrategy(ABC):
    """Abstract Strategy interface for pathfinding algorithms."""

    @abstractmethod
    def find_path(
        self,
        network: RoadNetwork,
        start_node: str,
        target_node: str,
        objective: RouteObjective,
        travel_mode: str = "VEHICLE",
    ) -> Optional[Dict[str, Any]]:
        """Calculates optimal path from start_node to target_node."""
        pass


class DijkstraStrategy(RouteStrategy):
    """Shortest/least-cost path calculation using Dijkstra's algorithm."""

    def find_path(
        self,
        network: RoadNetwork,
        start_node: str,
        target_node: str,
        objective: RouteObjective,
        travel_mode: str = "VEHICLE",
    ) -> Optional[Dict[str, Any]]:
        cost_fn = lambda edge: compute_edge_cost(edge, objective, travel_mode)
        return dijkstra_search(network.adjacency, start_node, target_node, cost_fn)


class AStarStrategy(RouteStrategy):
    """Heuristic-driven least-cost path calculation using A*."""

    def find_path(
        self,
        network: RoadNetwork,
        start_node: str,
        target_node: str,
        objective: RouteObjective,
        travel_mode: str = "VEHICLE",
    ) -> Optional[Dict[str, Any]]:
        cost_fn = lambda edge: compute_edge_cost(edge, objective, travel_mode)
        node_coords = network.get_node_coordinates()
        return astar_search(
            network.adjacency, node_coords, start_node, target_node, cost_fn
        )


class RouteEngine:
    """Coordinates route strategies and executes pathfinding."""

    def __init__(self):
        self._strategies: Dict[RoutingAlgorithm, RouteStrategy] = {
            RoutingAlgorithm.DIJKSTRA: DijkstraStrategy(),
            RoutingAlgorithm.ASTAR: AStarStrategy(),
        }

    def compute_path(
        self,
        network: RoadNetwork,
        start_node: str,
        target_node: str,
        objective: RouteObjective = RouteObjective.BALANCED,
        algorithm: RoutingAlgorithm = RoutingAlgorithm.ASTAR,
        travel_mode: str = "VEHICLE",
    ) -> Optional[Dict[str, Any]]:
        """Invokes appropriate pathfinding algorithm strategy."""
        strategy = self._strategies.get(algorithm, self._strategies[RoutingAlgorithm.ASTAR])
        return strategy.find_path(network, start_node, target_node, objective, travel_mode)
