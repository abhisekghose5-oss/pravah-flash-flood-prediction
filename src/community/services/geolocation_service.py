"""
PRAVAH — Geolocation & Spatial Telemetry Service
Provides coordinate validation, spatial bounding, distance metrics,
and proximity correlation to official PRAVAH gauge stations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from src.community.utils.helpers import haversine_distance_km

# Reference coordinates for core PRAVAH telemetry stations (for proximity context)
REFERENCE_GAUGE_STATIONS = [
    # Maharashtra Western Ghats
    {"id": "MH_GAK_12", "name": "Karad", "river": "Krishna", "region": "Maharashtra", "lat": 17.2889, "lng": 74.1844},
    {"id": "MH_GAK_17", "name": "Mahad", "river": "Savitri", "region": "Maharashtra", "lat": 18.0833, "lng": 73.4167},
    {"id": "MH_GAK_08", "name": "Chiplun", "river": "Vashishti", "region": "Maharashtra", "lat": 17.5323, "lng": 73.5186},
    {"id": "MH_GAK_04", "name": "Panchgani", "river": "Krishna Basin", "region": "Maharashtra", "lat": 17.9237, "lng": 73.8016},
    {"id": "MH_GAK_01", "name": "Lonavala", "river": "Indrayani", "region": "Maharashtra", "lat": 18.7557, "lng": 73.4091},
    {"id": "MH_GAK_02", "name": "Radhanagari", "river": "Bhogavati", "region": "Maharashtra", "lat": 16.4167, "lng": 73.9833},
    {"id": "MH_GAK_14", "name": "Kolhapur", "river": "Panchganga", "region": "Maharashtra", "lat": 16.7050, "lng": 74.2433},
    
    # Northeast Brahmaputra Basin
    {"id": "NE_AS_01", "name": "Beki", "river": "Beki / Manas", "region": "Northeast", "lat": 26.4983, "lng": 90.9192},
    {"id": "NE_AS_02", "name": "Dhubri", "river": "Brahmaputra", "region": "Northeast", "lat": 26.0205, "lng": 89.9754},
    {"id": "NE_AS_03", "name": "Goalpara", "river": "Brahmaputra", "region": "Northeast", "lat": 26.1750, "lng": 90.6250},
    {"id": "NE_AS_04", "name": "Guwahati", "river": "Brahmaputra", "region": "Northeast", "lat": 26.1878, "lng": 91.6916},
    {"id": "NE_AS_05", "name": "Tezpur", "river": "Brahmaputra", "region": "Northeast", "lat": 26.6528, "lng": 92.7925},
    {"id": "NE_AS_06", "name": "Dibrugarh", "river": "Brahmaputra", "region": "Northeast", "lat": 27.4526, "lng": 94.8972},
    {"id": "NE_AS_07", "name": "Silchar", "river": "Barak", "region": "Northeast", "lat": 24.8333, "lng": 92.7789},
]


def find_nearest_gauge_station(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Find the closest PRAVAH monitoring gauge station to the incident location.
    Returns station metadata and distance in kilometers.
    """
    nearest = None
    min_dist = float("inf")

    for stn in REFERENCE_GAUGE_STATIONS:
        dist = haversine_distance_km(lat, lon, stn["lat"], stn["lng"])
        if dist < min_dist:
            min_dist = dist
            nearest = {
                "station_id": stn["id"],
                "station_name": stn["name"],
                "river": stn["river"],
                "region": stn["region"],
                "distance_km": round(dist, 2),
            }

    return nearest


def is_within_regional_bounds(lat: float, lon: float, region: str) -> bool:
    """Check if coordinates fall within the specified region boundaries."""
    norm = region.lower().strip()
    if norm in ("northeast", "ne"):
        return 23.5 <= lat <= 29.5 and 88.5 <= lon <= 98.0
    elif norm in ("maharashtra", "mh"):
        return 15.0 <= lat <= 22.5 and 72.0 <= lon <= 81.0
    return True
