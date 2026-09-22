"""
PRAVAH Flood Propagation — River Overflow Scenario Calculator.
Models lateral bank breach, overtopping discharge, and backwater floodplain spreading.
"""

import math
from typing import Any, Dict, Tuple

from src.simulation.models.scenario import RiverOverflowScenarioParams
from src.simulation.utils.simulation_utils import propagation_fraction


class RiverOverflowScenario:
    """
    Hydraulic overtopping and breach inundation model for river flood cresting.
    """

    def __init__(self, params: RiverOverflowScenarioParams):
        self.params = params
        self.river_id = params.river_id

    def compute_propagation(
        self,
        elapsed_hours: float,
        total_period_hours: int,
        river_coords: Tuple[float, float]
    ) -> Dict[str, Any]:
        """
        Evaluate lateral breach inundation extent, depth, and spreading radius.
        """
        h_init = self.params.initial_water_level_m
        h_thresh = self.params.overflow_threshold_m
        h_sim = self.params.simulated_water_level_m
        dur = self.params.duration_hours
        w_breach = self.params.breach_width_m

        # Hydraulic head exceeding bank threshold
        head_excess = max(0.1, h_sim - h_thresh)

        # Broad-crested weir overtopping discharge equation:
        # Q = 1.7 * Width * Head^(1.5)
        q_spill = 1.7 * w_breach * (head_excess ** 1.5)

        # Max inundation footprint based on spill rate and duration
        max_extent_km2 = min(
            38.0,
            max(2.0, (q_spill / 450.0) * (dur ** 0.6) * 4.5)
        )

        # Maximum depth in breach depression
        max_depth_m = min(5.5, max(0.5, head_excess * 1.6))

        # Dynamic propagation fraction
        frac = propagation_fraction(elapsed_hours, max(dur * 1.5, float(total_period_hours)))

        current_extent = round(max_extent_km2 * frac, 2)
        current_depth = round(max(0.15, max_depth_m * math.sqrt(frac)), 2)
        radius_km = round(math.sqrt(current_extent / math.pi), 2) if current_extent > 0 else 0.15

        return {
            "elapsed_hours": elapsed_hours,
            "flooded_area_km2": current_extent,
            "max_potential_area_km2": round(max_extent_km2, 2),
            "peak_depth_m": current_depth,
            "max_potential_depth_m": round(max_depth_m, 2),
            "flood_radius_km": max(0.25, radius_km),
            "center_lat": river_coords[0],
            "center_lon": river_coords[1],
            "spill_discharge_m3s": round(q_spill, 2),
            "scenario_name": f"{self.params.river_name} Overtopping (+{round(head_excess, 1)}m breach)",
        }
