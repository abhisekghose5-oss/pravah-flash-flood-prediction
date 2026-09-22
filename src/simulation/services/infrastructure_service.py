"""
PRAVAH Flood Propagation — Infrastructure Impact Service.
Intersects advancing flood contours with road segments, bridges, hospitals,
and critical facilities to evaluate structural impact.
"""

import logging
import math
from typing import Dict, List, Optional

from src.simulation.models.impact import (
    InfrastructureCategory,
    InfrastructureImpactDetail,
    InfrastructureImpactSummary,
)
from src.simulation.utils.geo_utils import haversine_km

logger = logging.getLogger("pravah.simulation.infrastructure")


class InfrastructureService:
    """
    Evaluates physical and lifeline infrastructure exposure within simulated flood zones.
    """

    def __init__(self):
        # Database of key lifeline infrastructure across monitored corridors
        self.facilities_catalog = [
            {
                "id": "INF_HOSP_MHD_01",
                "name": "Mahad Rural Sub-District Hospital",
                "category": InfrastructureCategory.HOSPITALS,
                "lat": 18.0862,
                "lon": 73.4215,
                "catchment_id": "INDOFLOODS-gauge-602",
            },
            {
                "id": "INF_HOSP_KRD_01",
                "name": "Karad Krishna Charitable Hospital",
                "category": InfrastructureCategory.HOSPITALS,
                "lat": 17.2915,
                "lon": 74.1840,
                "catchment_id": "INDOFLOODS-gauge-684",
            },
            {
                "id": "INF_HOSP_KOL_01",
                "name": "Kolhapur CPR Civil Hospital",
                "category": InfrastructureCategory.HOSPITALS,
                "lat": 16.7020,
                "lon": 74.2410,
                "catchment_id": "INDOFLOODS-gauge-643",
            },
            {
                "id": "INF_BRG_MHD_01",
                "name": "Savitri River High-Level Bridge",
                "category": InfrastructureCategory.BRIDGES,
                "lat": 18.0910,
                "lon": 73.4310,
                "catchment_id": "INDOFLOODS-gauge-602",
            },
            {
                "id": "INF_BRG_KRD_01",
                "name": "Karad Pre-Stressed River Crossing",
                "category": InfrastructureCategory.BRIDGES,
                "lat": 17.2870,
                "lon": 74.1910,
                "catchment_id": "INDOFLOODS-gauge-684",
            },
            {
                "id": "INF_BRG_KOL_01",
                "name": "Panchganga Shivaji Bridge",
                "category": InfrastructureCategory.BRIDGES,
                "lat": 16.7110,
                "lon": 74.2380,
                "catchment_id": "INDOFLOODS-gauge-643",
            },
            {
                "id": "INF_SCH_MHD_01",
                "name": "Gandhari High School & Relief Camp",
                "category": InfrastructureCategory.SCHOOLS,
                "lat": 18.0820,
                "lon": 73.4180,
                "catchment_id": "INDOFLOODS-gauge-602",
            },
            {
                "id": "INF_SCH_KRD_01",
                "name": "Malkapur Municipal Vidyalaya",
                "category": InfrastructureCategory.SCHOOLS,
                "lat": 17.2990,
                "lon": 74.1780,
                "catchment_id": "INDOFLOODS-gauge-684",
            },
            {
                "id": "INF_PWR_MHD_01",
                "name": "MSEDCL 33kV Lowland Substation",
                "category": InfrastructureCategory.CRITICAL_FACILITIES,
                "lat": 18.0895,
                "lon": 73.4270,
                "catchment_id": "INDOFLOODS-gauge-602",
            },
            {
                "id": "INF_WTR_KRD_01",
                "name": "Krishna River Raw Water Intake Pump",
                "category": InfrastructureCategory.CRITICAL_FACILITIES,
                "lat": 17.2830,
                "lon": 74.1950,
                "catchment_id": "INDOFLOODS-gauge-684",
            },
        ]

    def evaluate_impact(
        self,
        center_lat: float,
        center_lon: float,
        flood_radius_km: float,
        peak_depth_m: float,
        catchment_id: str
    ) -> InfrastructureImpactSummary:
        """
        Intersect spatial flood radius with critical infrastructure assets
        and estimate submerged road segments and lengths.
        """
        detailed: List[InfrastructureImpactDetail] = []
        hospitals_count = 0
        bridges_count = 0
        schools_count = 0
        critical_count = 0

        for fac in self.facilities_catalog:
            dist = haversine_km(center_lat, center_lon, fac["lat"], fac["lon"])
            if dist <= flood_radius_km:
                # Water depth decays with distance from center
                depth_at_site = max(0.2, round(peak_depth_m * (1.0 - (dist / max(1.0, flood_radius_km)) * 0.7), 2))
                status = "SUBMERGED" if depth_at_site >= 0.8 else "THREATENED"

                cat = fac["category"]
                if cat == InfrastructureCategory.HOSPITALS:
                    hospitals_count += 1
                elif cat == InfrastructureCategory.BRIDGES:
                    bridges_count += 1
                elif cat == InfrastructureCategory.SCHOOLS:
                    schools_count += 1
                elif cat == InfrastructureCategory.CRITICAL_FACILITIES:
                    critical_count += 1

                detailed.append(
                    InfrastructureImpactDetail(
                        item_id=fac["id"],
                        name=fac["name"],
                        category=cat,
                        status=status,
                        estimated_water_depth_m=depth_at_site,
                        latitude=fac["lat"],
                        longitude=fac["lon"],
                    )
                )

        # Estimate affected road segments based on radius
        # Average road density in Western Ghats catchments ~ 3.5 km / km²
        inundated_area = math.pi * (flood_radius_km ** 2)
        submerged_road_km = round(min(85.0, inundated_area * 1.8), 1)
        submerged_segments = max(1, int(submerged_road_km / 1.5))

        # At least 1 bridge affected if flood radius > 2.5 km
        if flood_radius_km > 2.5 and bridges_count == 0:
            bridges_count = 1

        return InfrastructureImpactSummary(
            submerged_road_segments=submerged_segments,
            submerged_road_length_km=submerged_road_km,
            submerged_bridges=bridges_count,
            threatened_hospitals=hospitals_count,
            threatened_schools=schools_count,
            threatened_critical_facilities=critical_count,
            detailed_items=detailed,
        )
