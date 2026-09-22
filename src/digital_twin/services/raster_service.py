"""
PRAVAH Digital Twin — Raster & Accumulation Spatial Layer Service.
Synthesizes water accumulation zones, runoff intensity maps, and GeoJSON visualization layers.
"""

import math
import logging
from typing import Any, Dict, List, Tuple

from src.digital_twin.models.watershed import Watershed
from src.digital_twin.models.simulation import (
    AccumulationZone,
    AccumulationSeverity,
    WaterFlowParticle,
)
from src.digital_twin.utils.geo_utils import generate_offset_polygon

logger = logging.getLogger("pravah.digital_twin.raster")


class RasterService:
    """
    Generates spatial accumulation grids, flood risk polygons,
    and drainage network vectors for Leaflet visualization.
    """

    def generate_accumulation_layers(
        self,
        watershed: Watershed,
        direct_runoff_depth_mm: float,
        rainfall_intensity_mmhr: float,
    ) -> Tuple[List[AccumulationZone], Dict[str, Any]]:
        """
        Derive classified water accumulation zones and a styled GeoJSON FeatureCollection.
        Zones are categorized into LOW, MODERATE, HIGH, EXTREME based on physical depth potentials.
        """
        props = watershed.properties
        c_lat = props.centroid_lat
        c_lon = props.centroid_lon
        area = props.drainage_area_sqkm

        # Runoff scaling factor: higher runoff -> larger accumulation footprint & depth
        intensity_factor = min(3.0, max(0.5, direct_runoff_depth_mm / 40.0))

        # 4 distinct depression/riparian zones inside the catchment
        zones_def = [
            {
                "id": f"{props.watershed_id}_ZONE_EXTREME",
                "severity": AccumulationSeverity.EXTREME,
                "depth_range_m": "> 3.0m",
                "depth_val": 3.4 * intensity_factor,
                "area_pct": min(18.0, 4.0 * intensity_factor),
                "radius_km": max(0.8, math.sqrt(area) * 0.12 * intensity_factor),
                "d_lat": -0.015,
                "d_lon": 0.010,
                "color": "#ef4444",   # Red
                "fill_color": "#dc2626",
                "opacity": 0.65,
            },
            {
                "id": f"{props.watershed_id}_ZONE_HIGH",
                "severity": AccumulationSeverity.HIGH,
                "depth_range_m": "1.5m - 3.0m",
                "depth_val": 2.2 * intensity_factor,
                "area_pct": min(28.0, 8.5 * intensity_factor),
                "radius_km": max(1.2, math.sqrt(area) * 0.18 * intensity_factor),
                "d_lat": 0.008,
                "d_lon": -0.012,
                "color": "#f97316",   # Orange
                "fill_color": "#ea580c",
                "opacity": 0.55,
            },
            {
                "id": f"{props.watershed_id}_ZONE_MODERATE",
                "severity": AccumulationSeverity.MODERATE,
                "depth_range_m": "0.5m - 1.5m",
                "depth_val": 1.1 * intensity_factor,
                "area_pct": min(35.0, 15.0 * intensity_factor),
                "radius_km": max(1.8, math.sqrt(area) * 0.25 * intensity_factor),
                "d_lat": 0.022,
                "d_lon": 0.018,
                "color": "#eab308",   # Yellow
                "fill_color": "#ca8a04",
                "opacity": 0.45,
            },
            {
                "id": f"{props.watershed_id}_ZONE_LOW",
                "severity": AccumulationSeverity.LOW,
                "depth_range_m": "< 0.5m",
                "depth_val": 0.3 * intensity_factor,
                "area_pct": max(20.0, 45.0 - 15.0 * intensity_factor),
                "radius_km": max(2.5, math.sqrt(area) * 0.35 * intensity_factor),
                "d_lat": -0.025,
                "d_lon": -0.020,
                "color": "#06b6d4",   # Cyan
                "fill_color": "#0891b2",
                "opacity": 0.35,
            },
        ]

        accumulation_zones: List[AccumulationZone] = []
        geojson_features: List[Dict[str, Any]] = []

        for z in zones_def:
            z_lat = c_lat + z["d_lat"]
            z_lon = c_lon + z["d_lon"]
            z_area = round(area * (z["area_pct"] / 100.0), 2)

            poly_geom = generate_offset_polygon(
                center_lat=z_lat,
                center_lon=z_lon,
                radius_km=z["radius_km"],
                points_count=20,
                distortion_seed=z["depth_val"],
            )

            acc_zone = AccumulationZone(
                zone_id=z["id"],
                severity=z["severity"],
                depth_range_m=z["depth_range_m"],
                area_sqkm=z_area,
                area_percentage=round(z["area_pct"], 1),
                center_coordinates=[round(z_lon, 5), round(z_lat, 5)],
                geojson_polygon=poly_geom,
            )
            accumulation_zones.append(acc_zone)

            # Rich Leaflet Feature
            geojson_features.append({
                "type": "Feature",
                "id": z["id"],
                "properties": {
                    "zone_id": z["id"],
                    "severity": z["severity"].value,
                    "depth_range": z["depth_range_m"],
                    "area_sqkm": z_area,
                    "area_percentage": round(z["area_pct"], 1),
                    "stroke_color": z["color"],
                    "fill_color": z["fill_color"],
                    "fill_opacity": z["opacity"],
                    "label": f"{z['severity'].value} Accumulation ({z['depth_range_m']})",
                },
                "geometry": poly_geom,
            })

        fc = {
            "type": "FeatureCollection",
            "features": geojson_features,
        }
        return accumulation_zones, fc

    def generate_flow_network(
        self,
        watershed: Watershed
    ) -> Tuple[List[Dict[str, Any]], List[WaterFlowParticle]]:
        """
        Generate river channel polylines and animated water movement particle trajectories.
        Particles follow hydraulic routing down Strahler orders to the outlet.
        """
        props = watershed.properties
        c_lat = props.centroid_lat
        c_lon = props.centroid_lon
        outlet_lat = props.centroid_lat - 0.035
        outlet_lon = props.centroid_lon + 0.025

        # 3 stream branches (tributary left, tributary right, main trunk channel)
        segments_data = [
            # Main river trunk (Strahler Order 4/5)
            {
                "id": f"{props.watershed_id}_TRUNK",
                "name": f"{props.river_name} Main Channel",
                "order": props.stream_order,
                "color": "#38bdf8",
                "weight": 5,
                "coords": [
                    [c_lon - 0.015, c_lat + 0.025],
                    [c_lon - 0.005, c_lat + 0.010],
                    [c_lon + 0.005, c_lat - 0.010],
                    [outlet_lon, outlet_lat],
                ]
            },
            # Western Tributary (Strahler Order 2)
            {
                "id": f"{props.watershed_id}_TRIB_WEST",
                "name": f"{props.river_name} Western Tributary",
                "order": max(1, props.stream_order - 1),
                "color": "#818cf8",
                "weight": 3,
                "coords": [
                    [c_lon - 0.045, c_lat + 0.040],
                    [c_lon - 0.030, c_lat + 0.025],
                    [c_lon - 0.015, c_lat + 0.025],
                ]
            },
            # Eastern Headwater (Strahler Order 1)
            {
                "id": f"{props.watershed_id}_TRIB_EAST",
                "name": f"{props.river_name} Eastern Feeder",
                "order": max(1, props.stream_order - 2),
                "color": "#a78bfa",
                "weight": 2,
                "coords": [
                    [c_lon + 0.035, c_lat + 0.035],
                    [c_lon + 0.020, c_lat + 0.015],
                    [c_lon - 0.005, c_lat + 0.010],
                ]
            }
        ]

        geojson_segments: List[Dict[str, Any]] = []
        particles: List[WaterFlowParticle] = []
        p_idx = 0

        for seg in segments_data:
            line_geom = {
                "type": "LineString",
                "coordinates": seg["coords"]
            }
            geojson_segments.append({
                "type": "Feature",
                "id": seg["id"],
                "properties": {
                    "segment_id": seg["id"],
                    "river_name": seg["name"],
                    "stream_order": seg["order"],
                    "color": seg["color"],
                    "weight": seg["weight"],
                },
                "geometry": line_geom
            })

            # Create particles along each vertex hop
            pts = seg["coords"]
            for i in range(len(pts) - 1):
                p_idx += 1
                particles.append(
                    WaterFlowParticle(
                        particle_id=f"P_{props.watershed_id}_{p_idx}",
                        source_lat=pts[i][1],
                        source_lon=pts[i][0],
                        dest_lat=pts[i + 1][1],
                        dest_lon=pts[i + 1][0],
                        velocity_mps=round(1.0 + 0.4 * seg["order"], 2),
                        stream_order=seg["order"],
                        time_offset_fraction=round((i / max(1, len(pts) - 1)), 2),
                    )
                )

        return geojson_segments, particles
