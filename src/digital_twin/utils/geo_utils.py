"""
PRAVAH Digital Twin — Geospatial Utilities.
Provides coordinate transformations, bounding boxes, centroid calculation,
Haversine distances, polygon area estimations, and GeoJSON validation.
"""

import math
from typing import Any, Dict, List, Tuple


def validate_crs(crs: str) -> bool:
    """Validate that the CRS is compatible with WGS84 standard."""
    if not crs:
        return True
    cleaned = crs.strip().upper()
    return "4326" in cleaned or "WGS84" in cleaned or "CRS84" in cleaned


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth's mean radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def calculate_bbox(coordinates: Any) -> List[float]:
    """
    Calculate [min_lon, min_lat, max_lon, max_lat] from nested GeoJSON coordinate arrays.
    """
    min_lon, min_lat = float("inf"), float("inf")
    max_lon, max_lat = float("-inf"), float("-inf")

    def _extract_points(nested: Any):
        nonlocal min_lon, min_lat, max_lon, max_lat
        if isinstance(nested, (list, tuple)):
            if len(nested) >= 2 and isinstance(nested[0], (int, float)) and isinstance(nested[1], (int, float)):
                lon, lat = float(nested[0]), float(nested[1])
                min_lon = min(min_lon, lon)
                max_lon = max(max_lon, lon)
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)
            else:
                for item in nested:
                    _extract_points(item)

    _extract_points(coordinates)
    if min_lon == float("inf"):
        return [73.0, 16.0, 75.0, 19.0]
    return [round(min_lon, 5), round(min_lat, 5), round(max_lon, 5), round(max_lat, 5)]


def calculate_centroid(coordinates: Any) -> Tuple[float, float]:
    """
    Calculate representative centroid [latitude, longitude] from nested GeoJSON coordinates.
    """
    total_lat, total_lon, count = 0.0, 0.0, 0

    def _accumulate_points(nested: Any):
        nonlocal total_lat, total_lon, count
        if isinstance(nested, (list, tuple)):
            if len(nested) >= 2 and isinstance(nested[0], (int, float)) and isinstance(nested[1], (int, float)):
                total_lon += float(nested[0])
                total_lat += float(nested[1])
                count += 1
            else:
                for item in nested:
                    _accumulate_points(item)

    _accumulate_points(coordinates)
    if count == 0:
        return 17.0, 74.0
    return round(total_lat / count, 5), round(total_lon / count, 5)


def polygon_area_sqkm(coordinates: List[List[float]]) -> float:
    """
    Estimate polygon area in square kilometers using spherical excess / planar projection.
    Coordinates must be [[lon, lat], [lon, lat], ...].
    """
    if len(coordinates) < 3:
        return 0.0

    # Mean latitude in radians for cos projection
    mean_lat_rad = math.radians(sum(p[1] for p in coordinates) / len(coordinates))
    kx = 111.320 * math.cos(mean_lat_rad)  # km per degree lon
    ky = 110.574                          # km per degree lat

    area = 0.0
    j = len(coordinates) - 1
    for i in range(len(coordinates)):
        xi = coordinates[i][0] * kx
        yi = coordinates[i][1] * ky
        xj = coordinates[j][0] * kx
        yj = coordinates[j][1] * ky
        area += (xj + xi) * (yj - yi)
        j = i

    return abs(area / 2.0)


def generate_offset_polygon(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    points_count: int = 16,
    distortion_seed: float = 1.0
) -> Dict[str, Any]:
    """
    Generate an elliptical/organic polygon around a center point in GeoJSON Polygon format.
    Useful for synthetic accumulation basins and depression storage zones.
    """
    coords = []
    lat_km = 110.574
    lon_km = 111.320 * math.cos(math.radians(center_lat))

    for i in range(points_count):
        angle = 2.0 * math.pi * i / points_count
        # Add slight pseudo-random organic variation using sine harmonics
        var = 1.0 + 0.25 * math.sin(3.0 * angle + distortion_seed)
        r = radius_km * var
        d_lat = (r * math.sin(angle)) / lat_km
        d_lon = (r * math.cos(angle)) / lon_km
        coords.append([round(center_lon + d_lon, 5), round(center_lat + d_lat, 5)])

    # Close the ring
    coords.append(coords[0])
    return {
        "type": "Polygon",
        "coordinates": [coords]
    }
