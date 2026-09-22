"""Dijkstra's Shortest Path Algorithm for Road Network Graph."""
import heapq
import math
from typing import Dict, List, Optional, Tuple, Any, Callable


def dijkstra_search(
    adjacency_list: Dict[str, List[Dict[str, Any]]],
    start_node: str,
    target_node: str,
    cost_fn: Callable[[Dict[str, Any]], float],
) -> Optional[Dict[str, Any]]:
    """
    Executes Dijkstra's algorithm from start_node to target_node.

    :param adjacency_list: Mapping of node_id -> list of edge dictionaries.
           Each edge dict has: 'to_node', 'distance_km', 'status', 'flood_risk', etc.
    :param start_node: Source intersection ID.
    :param target_node: Destination intersection/shelter ID.
    :param cost_fn: Evaluates an edge dict to return a non-negative float weight,
                    or math.inf if the edge is impassable (e.g. CLOSED road).
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

    # Priority queue: (current_cost, current_node)
    pq: List[Tuple[float, str]] = [(0.0, start_node)]
    best_cost: Dict[str, float] = {start_node: 0.0}
    predecessor: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    closures_avoided = 0

    while pq:
        curr_cost, u = heapq.heappop(pq)

        if curr_cost > best_cost.get(u, math.inf):
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

            new_cost = curr_cost + weight
            if new_cost < best_cost.get(v, math.inf):
                best_cost[v] = new_cost
                predecessor[v] = (u, edge)
                heapq.heappush(pq, (new_cost, v))

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
        "total_cost": round(best_cost[target_node], 4),
        "total_distance_km": round(total_dist, 3),
        "avg_risk": round(avg_risk, 3),
        "max_risk": round(max_risk, 3),
        "closures_avoided": closures_avoided,
    }
