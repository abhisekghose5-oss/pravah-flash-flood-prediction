"""
PRAVAH Flood Propagation — Rainfall Scenario Calculator.
Computes precipitation runoff wave growth, maximum inundation footprint, and depth evolution.
"""

import math
from typing import Any, Dict, Tuple

from src.simulation.models.scenario import RainfallScenarioParams
from src.simulation.utils.simulation_utils import propagation_fraction


class RainfallScenario:
    """
    Hydrological propagation model for precipitation-driven flood events.
    """

    def __init__(self, params: RainfallScenarioParams):
        self.params = params
        self.catchment_id = params.catchment_id

    def compute_propagation(
        self,
        elapsed_hours: float,
        total_period_hours: int,
        centroid: Tuple[float, float],
        base_area_km2: float = 850.0
    ) -> Dict[str, Any]:
        """
        Evaluate flood extent footprint, peak depth, and radius at elapsed time t.
        """
        p = self.params.rainfall_mm
        dur = self.params.rainfall_duration_hours

        # Direct runoff proxy (SCS curve number approximation)
        ia = 20.0
        q_mm = ((p - ia) ** 2) / (p + 80.0) if p > ia else 0.0

        # Maximum potential flooded extent in km²
        # Max extent scales with runoff depth and catchment size
        max_extent_km2 = min(
            base_area_km2 * 0.28,
            max(2.5, 4.0 + (q_mm / 15.0) * (math.sqrt(base_area_km2) * 0.45))
        )

        # Max flood depth in meters
        max_depth_m = min(6.5, max(0.4, 0.5 + (p / 80.0) * 0.95))

        # Dynamic growth fraction at elapsed time t
        frac = propagation_fraction(elapsed_hours, max(dur * 1.5, float(total_period_hours)))

        current_extent = round(max_extent_km2 * frac, 2)
        current_depth = round(max(0.15, max_depth_m * math.sqrt(frac)), 2)

        # Flood radius in km: Area = pi * r^2 -> r = sqrt(Area / pi)
        radius_km = round(math.sqrt(current_extent / math.pi), 2) if current_extent > 0 else 0.1

        return {
            "elapsed_hours": elapsed_hours,
            "flooded_area_km2": current_extent,
            "max_potential_area_km2": round(max_extent_km2, 2),
            "peak_depth_m": current_depth,
            "max_potential_depth_m": round(max_depth_m, 2),
            "flood_radius_km": max(0.2, radius_km),
            "center_lat": centroid[0],
            "center_lon": centroid[1],
            "scenario_name": f"Heavy Rainfall ({p}mm in {dur}h)",
        }
