"""Road closure tracking and community hazard ingestion service."""
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from src.evacuation.models.road import RoadStatus


class RoadClosureService:
    """Manages active road closures, blockages, and partial obstructions."""

    def __init__(self):
        self._closures: Dict[str, Dict[str, Any]] = self._seed_closures()

    def _seed_closures(self) -> Dict[str, Dict[str, Any]]:
        """Pre-seeds realistic road blockages along critical corridors."""
        return {
            "RD-PUNE-OLD-BRIDGE": {
                "road_id": "RD-PUNE-OLD-BRIDGE",
                "name": "Old Lakdi Pul (Submerged Bridge)",
                "status": RoadStatus.CLOSED.value,
                "cause": "Mula-Mutha river cresting 0.8m over bridge deck",
                "reported_at": "2026-09-22T08:00:00Z",
                "verified": True,
                "coordinates": [[18.5160, 73.8440], [18.5190, 73.8470]],
            },
            "RD-KARAD-RIVER-ROAD": {
                "road_id": "RD-KARAD-RIVER-ROAD",
                "name": "Koyna Riverbank Lowland Pass",
                "status": RoadStatus.CLOSED.value,
                "cause": "Severe flash flood inundation across 400m carriageway",
                "reported_at": "2026-09-22T08:15:00Z",
                "verified": True,
                "coordinates": [[17.2880, 74.1780], [17.2920, 74.1860]],
            },
            "RD-MAHAD-BYPASS": {
                "road_id": "RD-MAHAD-BYPASS",
                "name": "Savitri North Embankment Road",
                "status": RoadStatus.PARTIALLY_BLOCKED.value,
                "cause": "Debris and standing water; single-lane crawl",
                "reported_at": "2026-09-22T08:30:00Z",
                "verified": True,
                "coordinates": [[18.0780, 73.4180], [18.0840, 73.4280]],
            },
            "RD-GUWAHATI-MG-ROAD": {
                "road_id": "RD-GUWAHATI-MG-ROAD",
                "name": "MG Road Riverfront Corridor",
                "status": RoadStatus.CLOSED.value,
                "cause": "Brahmaputra overflow along riverfront ghats",
                "reported_at": "2026-09-22T08:20:00Z",
                "verified": True,
                "coordinates": [[26.1880, 91.7480], [26.1920, 91.7580]],
            },
        }

    def get_all_closures(self) -> List[Dict[str, Any]]:
        """Returns list of all active closures."""
        return list(self._closures.values())

    def get_closure(self, road_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific closure by road ID."""
        return self._closures.get(road_id)

    def set_closure(
        self,
        road_id: str,
        name: str,
        status: RoadStatus,
        cause: str,
        coordinates: Optional[List[List[float]]] = None,
        verified: bool = True,
    ) -> Dict[str, Any]:
        """Registers or updates a road closure."""
        record = {
            "road_id": road_id,
            "name": name,
            "status": status.value if hasattr(status, "value") else str(status),
            "cause": cause,
            "reported_at": datetime.now(timezone.utc).isoformat(),
            "verified": verified,
            "coordinates": coordinates or [],
        }
        self._closures[road_id] = record
        return record

    def remove_closure(self, road_id: str) -> bool:
        """Clears a road closure if road reopened."""
        if road_id in self._closures:
            del self._closures[road_id]
            return True
        return False


road_closure_service = RoadClosureService()
