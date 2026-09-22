"""Shelter management repository and status tracker."""
from typing import List, Optional, Dict, Any
from src.data.db import get_relief_shelters, get_connection
from src.evacuation.models.shelter import Shelter, ShelterStatus


class ShelterService:
    """Provides access to and manages operational state of relief shelters."""

    def __init__(self):
        self._shelters_cache: Dict[str, Shelter] = {}
        self._load_initial_shelters()

    def _load_initial_shelters(self):
        """Loads shelters from SQLite and hydrates status metadata."""
        db_shelters = get_relief_shelters()
        for s in db_shelters:
            sid = f"SH-{s['id']}"
            cap = s.get("capacity") or 500
            # Realistic baseline occupancy (e.g. 40% capacity)
            occ = int(cap * 0.40)
            status = ShelterStatus.AVAILABLE
            if occ >= cap:
                status = ShelterStatus.FULL
            elif occ >= cap * 0.85:
                status = ShelterStatus.NEAR_CAPACITY

            shelter_obj = Shelter(
                id=sid,
                name=s["name"],
                latitude=float(s["latitude"]),
                longitude=float(s["longitude"]),
                capacity=cap,
                current_occupancy=occ,
                status=status,
                shelter_type=s.get("type", "Elevated Shelter"),
                region=s.get("region", "Maharashtra"),
                district=s.get("district"),
                contact=s.get("contact", "+91 112 / 1077"),
                accessibility_notes="Ramp accessible; 24/7 medical & food stores.",
            )
            self._shelters_cache[sid] = shelter_obj

    def get_all_shelters(self, region: Optional[str] = None) -> List[Shelter]:
        """Returns all relief shelters, optionally filtered by region."""
        shelters = list(self._shelters_cache.values())
        if region:
            norm = region.lower()
            return [s for s in shelters if s.region.lower() == norm]
        return shelters

    def get_available_shelters(self, region: Optional[str] = None) -> List[Shelter]:
        """Returns only shelters that are currently accepting evacuees."""
        all_s = self.get_all_shelters(region)
        return [s for s in all_s if s.is_accepting_evacuees]

    def get_shelter(self, shelter_id: str) -> Optional[Shelter]:
        """Retrieves single shelter by ID."""
        return self._shelters_cache.get(shelter_id)

    def update_shelter_status(
        self, shelter_id: str, status: ShelterStatus, occupancy: Optional[int] = None
    ) -> Optional[Shelter]:
        """Updates operational availability and occupancy count."""
        s = self._shelters_cache.get(shelter_id)
        if not s:
            return None
        s.status = status
        if occupancy is not None:
            s.current_occupancy = max(0, min(s.capacity, occupancy))
            if s.current_occupancy >= s.capacity:
                s.status = ShelterStatus.FULL
            elif s.current_occupancy >= s.capacity * 0.85 and s.status == ShelterStatus.AVAILABLE:
                s.status = ShelterStatus.NEAR_CAPACITY
        return s


shelter_service = ShelterService()
