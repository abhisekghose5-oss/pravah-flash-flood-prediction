"""
PRAVAH Flood Propagation — River & Dam Inventory Service.
Maintains hydraulic data for monitored river channels, warning/danger marks,
and major reservoirs across Western Ghats and Brahmaputra corridors.
"""

from typing import Any, Dict, List, Optional


class RiverService:
    """
    Catalog of monitored river reaches, threshold stages, and dam infrastructure.
    """

    def __init__(self):
        self.rivers_catalog: Dict[str, Dict[str, Any]] = {
            "RIVER_SAVITRI": {
                "river_id": "RIVER_SAVITRI",
                "name": "Savitri River",
                "basin": "West Flowing Rivers (Konkan)",
                "gauge_id": "INDOFLOODS-gauge-602",
                "station": "Mahad",
                "lat": 18.0922,
                "lon": 73.4603,
                "warning_level_m": 10.0,
                "danger_level_m": 11.0,
                "safe_discharge_m3s": 1800.0,
            },
            "RIVER_KRISHNA_KARAD": {
                "river_id": "RIVER_KRISHNA_KARAD",
                "name": "Krishna River (Karad)",
                "basin": "Krishna",
                "gauge_id": "INDOFLOODS-gauge-684",
                "station": "Karad",
                "lat": 17.2944,
                "lon": 74.1903,
                "warning_level_m": 563.4,
                "danger_level_m": 567.0,
                "safe_discharge_m3s": 4500.0,
            },
            "RIVER_PANCHGANGA": {
                "river_id": "RIVER_PANCHGANGA",
                "name": "Panchganga River",
                "basin": "Krishna",
                "gauge_id": "INDOFLOODS-gauge-643",
                "station": "Terwad",
                "lat": 16.6753,
                "lon": 74.5736,
                "warning_level_m": 534.0,
                "danger_level_m": 536.0,
                "safe_discharge_m3s": 2200.0,
            },
            "RIVER_ULHAS": {
                "river_id": "RIVER_ULHAS",
                "name": "Ulhas River",
                "basin": "Ulhas",
                "gauge_id": "INDOFLOODS-gauge-668",
                "station": "Badlapur",
                "lat": 19.1622,
                "lon": 73.2544,
                "warning_level_m": 16.5,
                "danger_level_m": 17.5,
                "safe_discharge_m3s": 1500.0,
            },
            "RIVER_BRAHMAPUTRA_BEKI": {
                "river_id": "RIVER_BRAHMAPUTRA_BEKI",
                "name": "Beki River (Brahmaputra Tributary)",
                "basin": "Brahmaputra",
                "gauge_id": "NE-Beki",
                "station": "Beki / Barpeta",
                "lat": 26.4983,
                "lon": 90.9192,
                "warning_level_m": 44.5,
                "danger_level_m": 45.1,
                "safe_discharge_m3s": 6000.0,
            },
        }

        self.dams_catalog: Dict[str, Dict[str, Any]] = {
            "DAM_KOYNA": {
                "dam_id": "DAM_KOYNA",
                "name": "Koyna Dam",
                "basin": "Krishna",
                "river": "Koyna",
                "lat": 17.4000,
                "lon": 73.7500,
                "gross_storage_mcm": 2797.4,
                "spillway_capacity_m3s": 5465.0,
                "downstream_reach": "Karad / Krishna Confluence",
                "downstream_catchment_id": "INDOFLOODS-gauge-684",
            },
            "DAM_UJANI": {
                "dam_id": "DAM_UJANI",
                "name": "Ujani Dam",
                "basin": "Krishna",
                "river": "Bhima",
                "lat": 18.0700,
                "lon": 75.1200,
                "gross_storage_mcm": 3140.0,
                "spillway_capacity_m3s": 7500.0,
                "downstream_reach": "Pandharpur / Solapur",
                "downstream_catchment_id": "INDOFLOODS-gauge-626",
            },
            "DAM_RADHANAGARI": {
                "dam_id": "DAM_RADHANAGARI",
                "name": "Radhanagari Dam",
                "basin": "Krishna",
                "river": "Bhogawati / Panchganga",
                "lat": 16.4167,
                "lon": 73.9833,
                "gross_storage_mcm": 236.8,
                "spillway_capacity_m3s": 1850.0,
                "downstream_reach": "Kolhapur City & Terwad",
                "downstream_catchment_id": "INDOFLOODS-gauge-643",
            },
            "DAM_BHATSA": {
                "dam_id": "DAM_BHATSA",
                "name": "Bhatsa Dam",
                "basin": "Ulhas",
                "river": "Bhatsa",
                "lat": 19.5300,
                "lon": 73.4300,
                "gross_storage_mcm": 976.0,
                "spillway_capacity_m3s": 3200.0,
                "downstream_reach": "Kalyan / Badlapur",
                "downstream_catchment_id": "INDOFLOODS-gauge-668",
            },
            "DAM_KHADAKWASLA": {
                "dam_id": "DAM_KHADAKWASLA",
                "name": "Khadakwasla Dam",
                "basin": "Krishna",
                "river": "Mutha",
                "lat": 18.4320,
                "lon": 73.7650,
                "gross_storage_mcm": 86.0,
                "spillway_capacity_m3s": 2750.0,
                "downstream_reach": "Pune Metropolitan Area",
                "downstream_catchment_id": "INDOFLOODS-gauge-640",
            },
        }

    def get_river(self, river_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve river hydraulic properties."""
        return self.rivers_catalog.get(river_id)

    def get_dam(self, dam_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve reservoir technical properties."""
        return self.dams_catalog.get(dam_id)

    def list_rivers(self) -> List[Dict[str, Any]]:
        return list(self.rivers_catalog.values())

    def list_dams(self) -> List[Dict[str, Any]]:
        return list(self.dams_catalog.values())
