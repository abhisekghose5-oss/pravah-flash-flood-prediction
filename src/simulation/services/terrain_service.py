"""
PRAVAH Flood Propagation — Terrain Support Service.
Provides catchment relief, elevation thresholds, and downvalley slope orientations.
"""

from typing import Any, Dict, Optional


class TerrainService:
    """
    Lightweight terrain proxy providing relief and slope parameters for flood propagation.
    """

    def __init__(self):
        # Default relief parameters for monitored catchments
        self.relief_defaults = {
            "INDOFLOODS-gauge-602": {"relief_m": 1350.0, "slope_deg": 14.5, "centroid": (18.0922, 73.4603)},
            "INDOFLOODS-gauge-684": {"relief_m": 836.0, "slope_deg": 8.5, "centroid": (17.2944, 74.1903)},
            "INDOFLOODS-gauge-643": {"relief_m": 458.0, "slope_deg": 4.5, "centroid": (16.6753, 74.5736)},
            "INDOFLOODS-gauge-668": {"relief_m": 1028.0, "slope_deg": 11.2, "centroid": (19.1622, 73.2544)},
            "NE-Beki": {"relief_m": 1250.0, "slope_deg": 3.8, "centroid": (26.4983, 90.9192)},
        }

    def get_terrain_profile(self, catchment_id: str) -> Dict[str, Any]:
        """Retrieve topographic relief, slope, and centroid coordinates."""
        return self.relief_defaults.get(catchment_id, {
            "relief_m": 650.0,
            "slope_deg": 7.0,
            "centroid": (18.0, 74.0),
        })
