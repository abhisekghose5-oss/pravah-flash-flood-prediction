"""Dynamic Road Network Graph with Spatial Topology."""
import math
from typing import Dict, List, Optional, Tuple, Any
from src.evacuation.utils.geo_utils import haversine_distance, interpolate_points
from src.evacuation.models.road import RoadStatus, RoadSegment


class RoadNetwork:
    """
    Topological road network representation for evacuation planning.
    Maintains spatial nodes (junctions, shelters, towns) and directed edges (road segments).
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.adjacency: Dict[str, List[Dict[str, Any]]] = {}
        self.edges_by_id: Dict[str, Dict[str, Any]] = {}

    def add_node(
        self,
        node_id: str,
        name: str,
        lat: float,
        lng: float,
        node_type: str = "intersection",
        shelter_id: Optional[str] = None,
    ):
        """Registers a spatial intersection, landmark, or shelter node."""
        self.nodes[node_id] = {
            "id": node_id,
            "name": name,
            "latitude": round(lat, 6),
            "longitude": round(lng, 6),
            "type": node_type,
            "shelter_id": shelter_id,
        }
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_edge(
        self,
        edge_id: str,
        from_node: str,
        to_node: str,
        name: str,
        distance_km: Optional[float] = None,
        base_speed_kmh: float = 40.0,
        flood_risk: float = 0.0,
        status: RoadStatus = RoadStatus.OPEN,
        cause: Optional[str] = None,
        bidirectional: bool = True,
        coordinates: Optional[List[List[float]]] = None,
    ):
        """Adds a road segment between two network nodes."""
        if from_node not in self.nodes or to_node not in self.nodes:
            return

        n1 = self.nodes[from_node]
        n2 = self.nodes[to_node]

        if distance_km is None:
            distance_km = haversine_distance(
                n1["latitude"], n1["longitude"], n2["latitude"], n2["longitude"]
            )
            distance_km = max(0.2, round(distance_km * 1.25, 2))  # Winding road factor

        if not coordinates:
            coordinates = interpolate_points(
                n1["latitude"], n1["longitude"], n2["latitude"], n2["longitude"], steps=4
            )

        edge_data_forward = {
            "id": edge_id,
            "name": name,
            "from_node": from_node,
            "to_node": to_node,
            "distance_km": round(distance_km, 3),
            "base_speed_kmh": base_speed_kmh,
            "flood_risk": round(float(flood_risk), 3),
            "status": status.value if hasattr(status, "value") else str(status),
            "cause": cause,
            "coordinates": coordinates,
        }

        self.adjacency[from_node].append(edge_data_forward)
        self.edges_by_id[edge_id] = edge_data_forward

        if bidirectional:
            rev_edge_id = f"{edge_id}_REV"
            edge_data_backward = {
                "id": rev_edge_id,
                "name": name,
                "from_node": to_node,
                "to_node": from_node,
                "distance_km": round(distance_km, 3),
                "base_speed_kmh": base_speed_kmh,
                "flood_risk": round(float(flood_risk), 3),
                "status": status.value if hasattr(status, "value") else str(status),
                "cause": cause,
                "coordinates": list(reversed(coordinates)),
            }
            self.adjacency[to_node].append(edge_data_backward)
            self.edges_by_id[rev_edge_id] = edge_data_backward

    def find_nearest_node(
        self, lat: float, lng: float, max_dist_km: float = 120.0
    ) -> Optional[str]:
        """Finds closest node in the road network to given coordinates."""
        best_node = None
        min_dist = math.inf
        for nid, node in self.nodes.items():
            d = haversine_distance(lat, lng, node["latitude"], node["longitude"])
            if d < min_dist and d <= max_dist_km:
                min_dist = d
                best_node = nid
        return best_node

    def update_edge_status(
        self, edge_id: str, status: RoadStatus, cause: Optional[str] = None
    ) -> bool:
        """Updates accessibility status on an edge and its bidirectional counterpart."""
        updated = False
        target_ids = [edge_id, f"{edge_id}_REV", edge_id.replace("_REV", "")]
        val = status.value if hasattr(status, "value") else str(status)

        for tid in target_ids:
            if tid in self.edges_by_id:
                self.edges_by_id[tid]["status"] = val
                if cause:
                    self.edges_by_id[tid]["cause"] = cause
                updated = True

        # Synchronize within adjacency lists
        for node, edges in self.adjacency.items():
            for e in edges:
                if e["id"] in target_ids:
                    e["status"] = val
                    if cause:
                        e["cause"] = cause
        return updated

    def update_edge_risk(self, edge_id: str, flood_risk: float) -> bool:
        """Updates flood risk score on edge and its counterpart."""
        updated = False
        target_ids = [edge_id, f"{edge_id}_REV", edge_id.replace("_REV", "")]
        r = round(max(0.0, min(1.0, float(flood_risk))), 3)

        for tid in target_ids:
            if tid in self.edges_by_id:
                self.edges_by_id[tid]["flood_risk"] = r
                updated = True

        for node, edges in self.adjacency.items():
            for e in edges:
                if e["id"] in target_ids:
                    e["flood_risk"] = r
        return updated

    def get_node_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """Returns map of node_id -> (latitude, longitude) for heuristic calculation."""
        return {nid: (n["latitude"], n["longitude"]) for nid, n in self.nodes.items()}

    def get_all_edges(self) -> List[Dict[str, Any]]:
        """Returns unique list of primary edge segments."""
        return [e for eid, e in self.edges_by_id.items() if not eid.endswith("_REV")]

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Returns list of all nodes."""
        return list(self.nodes.values())


def build_default_road_network() -> RoadNetwork:
    """
    Constructs comprehensive topological road graph connecting all 16 relief shelters
    and vital transit intersections across Maharashtra Western Ghats and Northeast corridors.
    """
    net = RoadNetwork()

    # =========================================================================
    # 1. PUNE / LONAVALA BASIN NODES & SHELTERS
    # =========================================================================
    net.add_node("NODE_PUNE_CENTRAL", "Pune Central Junction", 18.5204, 73.8567, "intersection")
    net.add_node("NODE_SHIVAJI_NAGAR", "Shivaji Nagar Elevated Shelter", 18.5312, 73.8445, "shelter", "SH-1")
    net.add_node("NODE_KOTHRUD_JUNCTION", "Kothrud Paud Road Junction", 18.5074, 73.8077, "intersection")
    net.add_node("NODE_KOTHRUD_SHELTER", "Kothrud Community High Ground Shelter", 18.5030, 73.8110, "shelter", "SH-2")
    net.add_node("NODE_SWARGATE", "Swargate Transport Interchange", 18.5018, 73.8586, "intersection")
    net.add_node("NODE_PIMPRI", "Pimpri Chinchwad Relief Ground", 18.6279, 73.7997, "shelter", "SH-3")
    net.add_node("NODE_DEHU_ROAD", "Dehu Road Highway Bypass", 18.7180, 73.7220, "intersection")
    net.add_node("NODE_LONAVALA_SHELTER", "Lonavala Municipal Disaster Shelter", 18.7546, 73.4062, "shelter", "SH-4")
    net.add_node("NODE_KHANDALA_PASS", "Khandala Ghat Safety Ridge", 18.7610, 73.3750, "intersection")

    # Connect Pune / Lonavala Edges
    net.add_edge("RD-PUN-01", "NODE_PUNE_CENTRAL", "NODE_SHIVAJI_NAGAR", "JM Road Flyover Corridor", 2.1, 45.0, 0.15)
    net.add_edge("RD-PUN-02", "NODE_PUNE_CENTRAL", "NODE_SWARGATE", "Bajirao Road High Corridor", 2.6, 35.0, 0.10)
    net.add_edge("RD-PUN-03", "NODE_SWARGATE", "NODE_KOTHRUD_JUNCTION", "Karve Road Elevated Arterial", 4.2, 40.0, 0.05)
    net.add_edge("RD-PUN-04", "NODE_KOTHRUD_JUNCTION", "NODE_KOTHRUD_SHELTER", "Paud Link Ramp", 0.8, 30.0, 0.0)
    net.add_edge("RD-PUN-05", "NODE_SHIVAJI_NAGAR", "NODE_PIMPRI", "Old Pune-Mumbai Highway NH-48", 12.5, 55.0, 0.18)
    net.add_edge("RD-PUN-06", "NODE_PIMPRI", "NODE_DEHU_ROAD", "Expressway Inflow Corridor", 11.2, 60.0, 0.10)
    net.add_edge("RD-PUN-07", "NODE_DEHU_ROAD", "NODE_LONAVALA_SHELTER", "Western Ghats Ascending Highway", 28.4, 50.0, 0.22)
    net.add_edge("RD-PUN-08", "NODE_LONAVALA_SHELTER", "NODE_KHANDALA_PASS", "Khandala Ridge Cutoff", 3.8, 40.0, 0.05)
    net.add_edge("RD-PUN-OLD-BRIDGE", "NODE_PUNE_CENTRAL", "NODE_SHIVAJI_NAGAR", "Old Lakdi Pul (Submerged Bridge)", 1.4, 25.0, 0.85, RoadStatus.CLOSED, "Mula-Mutha river cresting 0.8m over bridge deck")

    # =========================================================================
    # 2. SATARA / WAI / MAHABALESHWAR NODES & SHELTERS
    # =========================================================================
    net.add_node("NODE_SATARA_CENTRAL", "Satara Central Powai Naka", 17.6805, 74.0183, "intersection")
    net.add_node("NODE_SATARA_SHELTER", "Satara Elevated Polytech Camp", 17.6914, 74.0049, "shelter", "SH-5")
    net.add_node("NODE_WAI_JUNCTION", "Wai River Crossing Junction", 17.9482, 73.8920, "intersection")
    net.add_node("NODE_WAI_SHELTER", "Wai Tahsil Elevated Hall", 17.9520, 73.8860, "shelter", "SH-6")
    net.add_node("NODE_MAHABALESHWAR_SHELTER", "Mahabaleshwar Community Refuge", 17.9237, 73.6586, "shelter", "SH-7")

    # Connect Satara / Wai / Mahabaleshwar
    net.add_edge("RD-SAT-01", "NODE_SATARA_CENTRAL", "NODE_SATARA_SHELTER", "Ajinkyatara Ridge Road", 2.3, 35.0, 0.05)
    net.add_edge("RD-SAT-02", "NODE_SATARA_CENTRAL", "NODE_WAI_JUNCTION", "NH-48 Satara-Wai Connector", 34.0, 60.0, 0.15)
    net.add_edge("RD-SAT-03", "NODE_WAI_JUNCTION", "NODE_WAI_SHELTER", "Wai Town Bypass", 1.2, 30.0, 0.12)
    net.add_edge("RD-SAT-04", "NODE_WAI_JUNCTION", "NODE_MAHABALESHWAR_SHELTER", "Pasarni Ghat High Altitude Route", 24.5, 35.0, 0.20)
    net.add_edge("RD-SAT-05", "NODE_DEHU_ROAD", "NODE_SATARA_CENTRAL", "NH-48 Southbound Trunk", 115.0, 70.0, 0.10)

    # =========================================================================
    # 3. KARAD / KRISHNA-KOYNA NODES & SHELTERS
    # =========================================================================
    net.add_node("NODE_KARAD_CENTRAL", "Karad Town Square", 17.2890, 74.1810, "intersection")
    net.add_node("NODE_KARAD_SHELTER_1", "Karad Krishna Valley High School", 17.2845, 74.1925, "shelter", "SH-8")
    net.add_node("NODE_KARAD_BYPASS", "Karad Highway Overpass", 17.3020, 74.1750, "intersection")
    net.add_node("NODE_KOYNA_SHELTER", "Koyna River High Ridge Refuge", 17.3150, 74.1620, "shelter", "SH-9")

    # Connect Karad Edges
    net.add_edge("RD-KRD-01", "NODE_KARAD_CENTRAL", "NODE_KARAD_SHELTER_1", "Market Yard Elevated Approach", 1.6, 35.0, 0.10)
    net.add_edge("RD-KRD-02", "NODE_KARAD_CENTRAL", "NODE_KARAD_BYPASS", "Malkapur Link Way", 2.2, 45.0, 0.08)
    net.add_edge("RD-KRD-03", "NODE_KARAD_BYPASS", "NODE_KOYNA_SHELTER", "Western Ridge Scenic Highroad", 2.8, 40.0, 0.05)
    net.add_edge("RD-KRD-04", "NODE_SATARA_CENTRAL", "NODE_KARAD_BYPASS", "NH-48 Satara-Karad Expressway", 48.0, 65.0, 0.12)
    net.add_edge("RD-KARAD-RIVER-ROAD", "NODE_KARAD_CENTRAL", "NODE_KOYNA_SHELTER", "Koyna Riverbank Lowland Pass", 2.1, 20.0, 0.90, RoadStatus.CLOSED, "Severe flash flood inundation across 400m carriageway")

    # =========================================================================
    # 4. MAHAD & CHIPLUN NODES & SHELTERS (SAVITRI / VASHISHTI BASINS)
    # =========================================================================
    net.add_node("NODE_MAHAD_CENTRAL", "Mahad Shivaji Chowk", 18.0833, 73.4167, "intersection")
    net.add_node("NODE_MAHAD_SHELTER", "Mahad Disaster Relief Staging Area", 18.0920, 73.4250, "shelter", "SH-10")
    net.add_node("NODE_CHIPLUN_CENTRAL", "Chiplun Main Bazaar", 17.5323, 73.5178, "intersection")
    net.add_node("NODE_CHIPLUN_SHELTER", "Chiplun Flood Refuge Center", 17.5450, 73.5310, "shelter", "SH-11")

    net.add_edge("RD-MHD-01", "NODE_MAHAD_CENTRAL", "NODE_MAHAD_SHELTER", "Gandhari Elevated Bypass", 1.8, 35.0, 0.10)
    net.add_edge("RD-MAHAD-BYPASS", "NODE_MAHAD_CENTRAL", "NODE_MAHAD_SHELTER", "Savitri North Embankment Road", 2.2, 25.0, 0.48, RoadStatus.PARTIALLY_BLOCKED, "Debris and standing water; single-lane crawl")
    net.add_edge("RD-CHP-01", "NODE_CHIPLUN_CENTRAL", "NODE_CHIPLUN_SHELTER", "Bahadurshaikh Elevated Flyover", 2.4, 40.0, 0.12)
    net.add_edge("RD-MHD-CHP", "NODE_MAHAD_CENTRAL", "NODE_CHIPLUN_CENTRAL", "NH-66 Konkan Highway", 62.0, 50.0, 0.25)

    # =========================================================================
    # 5. KOLHAPUR NODES & SHELTERS (PANCHGANGA BASIN)
    # =========================================================================
    net.add_node("NODE_KOLHAPUR_CENTRAL", "Kolhapur CBS Bus Terminal", 16.7050, 74.2433, "intersection")
    net.add_node("NODE_KOLHAPUR_SHELTER_1", "Shivaji University Elevated Complex", 16.6780, 74.2540, "shelter", "SH-12")
    net.add_node("NODE_KOLHAPUR_SHELTER_2", "Mahaveer College High Ground Shelter", 16.7120, 74.2380, "shelter", "SH-13")

    net.add_edge("RD-KOL-01", "NODE_KOLHAPUR_CENTRAL", "NODE_KOLHAPUR_SHELTER_1", "University Road Elevated Bypass", 3.8, 40.0, 0.05)
    net.add_edge("RD-KOL-02", "NODE_KOLHAPUR_CENTRAL", "NODE_KOLHAPUR_SHELTER_2", "Bhausingji Road High Ground", 1.5, 30.0, 0.15)
    net.add_edge("RD-KRD-KOL", "NODE_KARAD_BYPASS", "NODE_KOLHAPUR_CENTRAL", "NH-48 Karad-Kolhapur Arterial", 68.0, 70.0, 0.10)

    # =========================================================================
    # 6. NORTHEAST BRAHMAPUTRA BASIN (GUWAHATI / BARPETA / KAZIRANGA)
    # =========================================================================
    net.add_node("NODE_GUWAHATI_CENTRAL", "Guwahati Paltan Bazar Junction", 26.1820, 91.7510, "intersection")
    net.add_node("NODE_JALUKBARI", "Jalukbari Elevated Rotary Shelter", 26.1550, 91.6680, "shelter", "SH-14")
    net.add_node("NODE_DISPUR", "Dispur Capital Complex Relief Camp", 26.1430, 91.7890, "shelter", "SH-15")
    net.add_node("NODE_KHANAPARA", "Khanapara Veterinary Field Shelter", 26.1180, 91.8210, "shelter", "SH-16")

    net.add_edge("RD-GHY-01", "NODE_GUWAHATI_CENTRAL", "NODE_JALUKBARI", "Guwahati University Trunk Way", 9.2, 45.0, 0.10)
    net.add_edge("RD-GHY-02", "NODE_GUWAHATI_CENTRAL", "NODE_DISPUR", "GS Road Elevated Corridor", 6.8, 40.0, 0.15)
    net.add_edge("RD-GHY-03", "NODE_DISPUR", "NODE_KHANAPARA", "Khanapara Expressway Approach", 4.1, 50.0, 0.05)
    net.add_edge("RD-GUWAHATI-MG-ROAD", "NODE_GUWAHATI_CENTRAL", "NODE_JALUKBARI", "MG Road Riverfront Corridor", 8.4, 25.0, 0.82, RoadStatus.CLOSED, "Brahmaputra overflow along riverfront ghats")

    return net

