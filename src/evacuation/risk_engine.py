"""Dynamic risk calculation and road network hazard synchronization."""
from typing import Dict, List, Any
from src.evacuation.road_network import RoadNetwork
from src.evacuation.services.flood_risk_service import flood_risk_service
from src.evacuation.services.road_closure_service import road_closure_service
from src.evacuation.models.road import RoadStatus
from src.evacuation.utils.geo_utils import haversine_distance


class RiskEngine:
    """Synchronizes dynamic flood hazard levels and closures onto the road network graph."""

    def __init__(self):
        pass

    def apply_hazards_to_network(self, network: RoadNetwork) -> int:
        """
        Evaluates active risk zones and road closures, updating road segment
        flood risk scores and accessibility statuses across the network.
        Returns total number of modified road segments.
        """
        modified_count = 0
        risk_zones = flood_risk_service.get_all_risk_zones()
        closures = road_closure_service.get_all_closures()
        closure_map = {c["road_id"]: c for c in closures}

        # 1. Update Road Closures
        for edge_id, edge in list(network.edges_by_id.items()):
            base_id = edge_id.replace("_REV", "")
            if base_id in closure_map:
                c = closure_map[base_id]
                status_str = c.get("status", "OPEN")
                st = RoadStatus(status_str) if status_str in RoadStatus.__members__ else RoadStatus.CLOSED
                network.update_edge_status(edge_id, st, cause=c.get("cause"))
                modified_count += 1

        # 2. Check spatial proximity to flood risk zones
        for edge_id, edge in list(network.edges_by_id.items()):
            coords = edge.get("coordinates", [])
            if not coords:
                continue

            # Check midpoint of edge against risk zones
            midpoint = coords[len(coords) // 2]
            m_lat, m_lng = midpoint[0], midpoint[1]

            max_zone_risk = 0.0
            for z in risk_zones:
                # Proximity to zone polygon center or vertices
                for pt in z.polygon:
                    dist = haversine_distance(m_lat, m_lng, pt[0], pt[1])
                    if dist <= 3.5:  # Within 3.5 km of active flood basin
                        proximity_weight = max(0.2, (3.5 - dist) / 3.5)
                        zone_risk = z.risk_score * proximity_weight
                        if zone_risk > max_zone_risk:
                            max_zone_risk = zone_risk

            if max_zone_risk > 0.0:
                # Blend with existing edge baseline
                current_risk = edge.get("flood_risk", 0.0)
                blended = round(max(current_risk, max_zone_risk), 3)
                network.update_edge_risk(edge_id, blended)
                modified_count += 1

        return modified_count


risk_engine = RiskEngine()
