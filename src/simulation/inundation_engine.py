"""
PRAVAH Flood Propagation — Inundation Spatial Layer Engine.
Generates multi-depth classified GeoJSON polygon layers representing
flood footprints and water depth bands at discrete time steps.
"""

import math
from typing import Any, Dict, List

from src.simulation.models.inundation import (
    DepthCategory,
    FloodSeverityClass,
    InundationDepthStats,
    TimeStepInundation,
)
from src.simulation.utils.geo_utils import generate_propagation_polygon


class InundationEngine:
    """
    Transforms hydraulic parameters into styled multi-tier geospatial inundation polygons.
    """

    def generate_timestep_inundation(
        self,
        time_hours: float,
        time_label: str,
        center_lat: float,
        center_lon: float,
        flood_radius_km: float,
        flooded_area_km2: float,
        peak_depth_m: float
    ) -> TimeStepInundation:
        """
        Synthesize classified flood extent polygons and depth distribution for a time step.
        """
        if flooded_area_km2 <= 0.01:
            # T+0h or dry pre-event state
            return TimeStepInundation(
                time_step_hours=time_hours,
                time_label=time_label,
                total_extent_km2=0.0,
                depth_stats=InundationDepthStats(
                    min_depth_m=0.0,
                    max_depth_m=0.0,
                    mean_depth_m=0.0,
                    predominant_category=DepthCategory.SHALLOW_0_05M,
                ),
                severity_breakdown_km2={
                    "LOW": 0.0, "MODERATE": 0.0, "HIGH": 0.0, "SEVERE": 0.0, "EXTREME": 0.0
                },
                geojson_feature_collection={
                    "type": "FeatureCollection",
                    "features": []
                }
            )

        # Depth zones definitions (nested expanding rings from deep center to shallow fringes)
        depth_tiers = [
            {
                "tier": "EXTREME",
                "depth_range": ">5.0m",
                "depth_cat": DepthCategory.EXTREME_GT_5M,
                "radius_frac": 0.22,
                "min_depth": 5.0,
                "stroke": "#7f1d1d",
                "fill": "#991b1b",
                "opacity": 0.75,
                "label": "Catastrophic (>5m)",
            },
            {
                "tier": "SEVERE",
                "depth_range": "2.0-5.0m",
                "depth_cat": DepthCategory.SEVERE_2_5M,
                "radius_frac": 0.42,
                "min_depth": 2.0,
                "stroke": "#be123c",
                "fill": "#f43f5e",
                "opacity": 0.65,
                "label": "Severe (2-5m)",
            },
            {
                "tier": "HIGH",
                "depth_range": "1.0-2.0m",
                "depth_cat": DepthCategory.DEEP_1_2M,
                "radius_frac": 0.65,
                "min_depth": 1.0,
                "stroke": "#c2410c",
                "fill": "#f97316",
                "opacity": 0.55,
                "label": "Deep (1-2m)",
            },
            {
                "tier": "MODERATE",
                "depth_range": "0.5-1.0m",
                "depth_cat": DepthCategory.MODERATE_05_1M,
                "radius_frac": 0.85,
                "min_depth": 0.5,
                "stroke": "#a16207",
                "fill": "#eab308",
                "opacity": 0.45,
                "label": "Moderate (0.5-1m)",
            },
            {
                "tier": "LOW",
                "depth_range": "0-0.5m",
                "depth_cat": DepthCategory.SHALLOW_0_05M,
                "radius_frac": 1.0,
                "min_depth": 0.1,
                "stroke": "#0e7490",
                "fill": "#06b6d4",
                "opacity": 0.35,
                "label": "Shallow (0-0.5m)",
            },
        ]

        features: List[Dict[str, Any]] = []
        severity_areas: Dict[str, float] = {}

        # Render tiers from largest (outer shallow ring) to smallest (inner deep ring)
        for idx, t in enumerate(reversed(depth_tiers)):
            if peak_depth_m < t["min_depth"] and t["tier"] in ["EXTREME", "SEVERE"]:
                continue  # Skip deeper tiers if peak depth does not reach them

            tier_radius = flood_radius_km * t["radius_frac"]
            tier_area = round(flooded_area_km2 * (t["radius_frac"] ** 2), 2)
            severity_areas[t["tier"]] = tier_area

            poly_geom = generate_propagation_polygon(
                center_lat=center_lat,
                center_lon=center_lon,
                radius_km=max(0.1, tier_radius),
                wave_noise=0.15 + 0.05 * idx,
            )

            features.append({
                "type": "Feature",
                "id": f"INUNDATION_{time_label}_{t['tier']}",
                "properties": {
                    "time_step": time_hours,
                    "time_label": time_label,
                    "severity": t["tier"],
                    "depth_category": t["depth_range"],
                    "area_km2": tier_area,
                    "stroke_color": t["stroke"],
                    "fill_color": t["fill"],
                    "fill_opacity": t["opacity"],
                    "label": f"{time_label} Inundation: {t['label']} (~{tier_area} km²)",
                },
                "geometry": poly_geom,
            })

        mean_depth = round(min(peak_depth_m, max(0.3, peak_depth_m * 0.55)), 2)

        predom_cat = DepthCategory.MODERATE_05_1M
        if peak_depth_m >= 4.0:
            predom_cat = DepthCategory.SEVERE_2_5M
        elif peak_depth_m < 0.8:
            predom_cat = DepthCategory.SHALLOW_0_05M

        return TimeStepInundation(
            time_step_hours=time_hours,
            time_label=time_label,
            total_extent_km2=flooded_area_km2,
            depth_stats=InundationDepthStats(
                min_depth_m=0.15,
                max_depth_m=peak_depth_m,
                mean_depth_m=mean_depth,
                predominant_category=predom_cat,
            ),
            severity_breakdown_km2=severity_areas,
            geojson_feature_collection={
                "type": "FeatureCollection",
                "features": features,
            }
        )
