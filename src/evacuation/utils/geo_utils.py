"""Geospatial utilities for evacuation pathfinding and distance calculations."""
import math
from typing import List, Tuple, Dict, Any

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS points in kilometers.
    """
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(EARTH_RADIUS_KM * c, 4)


def polyline_length(coords: List[List[float]]) -> float:
    """
    Calculates total length of a polyline in kilometers.
    coords format: [[lat, lon], [lat, lon], ...]
    """
    if len(coords) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coords) - 1):
        total += haversine_distance(
            coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1]
        )
    return round(total, 3)


def interpolate_points(
    lat1: float, lon1: float, lat2: float, lon2: float, steps: int = 5
) -> List[List[float]]:
    """
    Interpolates intermediate coordinate points between two locations.
    """
    points = []
    for i in range(steps + 1):
        frac = i / float(steps)
        ilat = lat1 + (lat2 - lat1) * frac
        ilon = lon1 + (lon2 - lon1) * frac
        points.append([round(ilat, 6), round(ilon, 6)])
    return points


def is_in_bounding_box(
    lat: float, lon: float, min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> bool:
    """Checks if coordinates fall inside bounding box."""
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
