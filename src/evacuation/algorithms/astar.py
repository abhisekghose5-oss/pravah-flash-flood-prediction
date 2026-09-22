"""A* Pathfinding Algorithm with Geographic Heuristic."""
import heapq
import math
from typing import Dict, List, Optional, Tuple, Any, Callable
from src.evacuation.utils.geo_utils import haversine_distance


def astar_search(
    adjacency_list: Dict[str, List[Dict[str, Any]]],
    node_coordinates: Dict[str, Tuple[float, float]],
    start_node: str,
    target_node: str,
    cost_fn: Callable[[Dict[str, Any]], float],
    heuristic_fn: Optional[Callable[[str, str], float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Executes A* search from start_node to target_node using admissible geographic heuristic.

    :param adjacency_list: Graph mapping node_id -> list of edge dicts.
    :param node_coordinates: Mapping node_id -> (lat, lon).
    :param start_node: Source intersection ID.
    :param target_node: Destination intersection/shelter ID.
    :param cost_fn: Evaluates an edge dict to return non-negative float cost.
    :param heuristic_fn: Optional custom heuristic h(u, v). If omitted, calculates
                         admissible straight-line travel time estimate.
    :return: Dictionary containing 'path', 'edges', 'total_cost', 'total_distance_km',
             'avg_risk', and 'closures_avoided', or None if unreachable.
    """
    if start_node not in adjacency_list or target_node not in adjacency_list:
        return None

    if start_node == target_node:
        return {
            "path": [start_node],
            "edges": [],
            "total_cost": 0.0,
            "total_distance_km": 0.0,
            "avg_risk": 0.0,
            "max_risk": 0.0,
            "closures_avoided": 0,
        }

    # Default heuristic: Haversine distance / 60 km/h (admissible travel cost in hours/mins)
    def default_heuristic(u: str, v: str) -> float:
        if u not in node_coordinates or v not in node_coordinates:
            return 0.0
        lat1, lon1 = node_coordinates[u]
        lat2, lon2 = node_coordinates[v]
        dist_km = haversine_distance(lat1, lon1, lat2, lon2)
        # 60 km/h = 1 km/min -> dist_km mins
        return dist_km

    h = heuristic_fn or default_heuristic

    # Priority queue stores: (f_score, g_score, node_id)
    start_h = h(start_node, target_node)
    pq: List[Tuple[float, float, str]] = [(start_h, 0.0, start_node)]

    g_score: Dict[str, float] = {start_node: 0.0}
    predecessor: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    closures_avoided = 0

    while pq:
        f, curr_g, u = heapq.heappop(pq)

        if curr_g > g_score.get(u, math.inf):
            continue

        if u == target_node:
            break

        for edge in adjacency_list.get(u, []):
            v = edge["to_node"]
            weight = cost_fn(edge)

            # Check if edge is impassable/closed
            if math.isinf(weight) or weight >= 1e8:
                if edge.get("status") == "CLOSED":
                    closures_avoided += 1
                continue

            tentative_g = curr_g + weight
            if tentative_g < g_score.get(v, math.inf):
                g_score[v] = tentative_g
                h_val = h(v, target_node)
                f_val = tentative_g + h_val
                predecessor[v] = (u, edge)
                heapq.heappush(pq, (f_val, tentative_g, v))

    if target_node not in predecessor and start_node != target_node:
        return None

    # Reconstruct path and traversed edges
    path: List[str] = []
    edges: List[Dict[str, Any]] = []
    curr = target_node

    while curr != start_node:
        path.append(curr)
        prev_node, edge_data = predecessor[curr]
        edges.append(edge_data)
        curr = prev_node

    path.append(start_node)
    path.reverse()
    edges.reverse()

    total_dist = sum(e.get("distance_km", 0.0) for e in edges)
    risks = [e.get("flood_risk", 0.0) for e in edges]
    avg_risk = sum(risks) / len(risks) if risks else 0.0
    max_risk = max(risks) if risks else 0.0

    return {
        "path": path,
        "edges": edges,
        "total_cost": round(g_score[target_node], 4),
        "total_distance_km": round(total_dist, 3),
        "avg_risk": round(avg_risk, 3),
        "max_risk": round(max_risk, 3),
        "closures_avoided": closures_avoided,
    }
