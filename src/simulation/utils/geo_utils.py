"""
PRAVAH Flood Propagation — Geospatial Utilities.
Provides spatial buffer geometry synthesis, coordinate distance, and GeoJSON polygon generation.
"""

import math
from typing import Any, Dict, List, Tuple


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two coordinates in kilometers."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def generate_propagation_polygon(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    eccentricity_east: float = 1.0,
    eccentricity_north: float = 0.8,
    wave_noise: float = 0.2,
    num_points: int = 24
) -> Dict[str, Any]:
    """
    Generate an asymmetrical expanding flood wave polygon reflecting downhill alluvial spreading.
    """
    coords = []
    lat_km = 110.574
    lon_km = 111.320 * math.cos(math.radians(center_lat))

    for i in range(num_points):
        theta = 2.0 * math.pi * i / num_points
        # Directional stretch (downvalley bias eastward/southeastward)
        stretch = 1.0 + 0.3 * math.sin(theta) + 0.2 * math.cos(theta)
        # Random harmonic wave ripple
        noise = 1.0 + wave_noise * math.sin(4.0 * theta)
        r = radius_km * stretch * noise

        d_lat = (r * math.sin(theta) * eccentricity_north) / lat_km
        d_lon = (r * math.cos(theta) * eccentricity_east) / lon_km

        coords.append([round(center_lon + d_lon, 5), round(center_lat + d_lat, 5)])

    # Close the ring
    coords.append(coords[0])
    return {
        "type": "Polygon",
        "coordinates": [coords]
    }


def is_point_within_radius(
    pt_lat: float, pt_lon: float,
    center_lat: float, center_lon: float,
    radius_km: float
) -> bool:
    """Check if point falls within circular/elliptical zone approximation."""
    dist = haversine_km(pt_lat, pt_lon, center_lat, center_lon)
    return dist <= radius_km
