"""
PRAVAH Flood Propagation — Dam Release Scenario Calculator.
Models downstream floodwave surge from emergency or scheduled reservoir discharges.
"""

import math
from typing import Any, Dict, Tuple

from src.simulation.models.scenario import DamReleaseScenarioParams
from src.simulation.utils.simulation_utils import propagation_fraction


class DamReleaseScenario:
    """
    Hydraulic floodwave routing model for dam/reservoir release events.
    """

    def __init__(self, params: DamReleaseScenarioParams):
        self.params = params
        self.dam_id = params.dam_id

    def compute_propagation(
        self,
        elapsed_hours: float,
        total_period_hours: int,
        dam_coords: Tuple[float, float],
        downstream_offset_deg: Tuple[float, float] = (-0.03, 0.04)
    ) -> Dict[str, Any]:
        """
        Evaluate flood extent, downstream surge propagation distance, and flood depth.
        """
        q_rel = self.params.release_rate_m3s
        q_safe = self.params.downstream_safe_capacity_m3s
        dur = self.params.release_duration_hours

        # Excess discharge above riverbank conveyance capacity
        q_excess = max(100.0, q_rel - q_safe)

        # Total release volume in Million Cubic Meters (MCM)
        vol_mcm = (q_rel * dur * 3600.0) / 1_000_000.0

        # Maximum inundated extent based on excess discharge and duration
        max_extent_km2 = min(
            65.0,
            max(4.0, (q_excess / 1200.0) * (dur ** 0.65) * 5.2)
        )

        # Peak flood depth in downstream channel
        max_depth_m = min(8.0, max(0.8, 1.2 + (q_excess / 1800.0) * 1.4))

        # Dynamic propagation fraction (floodwave arrives downstream over hours)
        frac = propagation_fraction(elapsed_hours, max(dur * 2.0, float(total_period_hours)))

        current_extent = round(max_extent_km2 * frac, 2)
        current_depth = round(max(0.2, max_depth_m * math.sqrt(frac)), 2)

        # Radius / buffer in km
        radius_km = round(math.sqrt(current_extent / math.pi), 2) if current_extent > 0 else 0.2

        # Floodwave centroid shifts downstream as water travels downvalley
        downstream_lat = dam_coords[0] + downstream_offset_deg[0] * frac
        downstream_lon = dam_coords[1] + downstream_offset_deg[1] * frac

        return {
            "elapsed_hours": elapsed_hours,
            "flooded_area_km2": current_extent,
            "max_potential_area_km2": round(max_extent_km2, 2),
            "peak_depth_m": current_depth,
            "max_potential_depth_m": round(max_depth_m, 2),
            "flood_radius_km": max(0.3, radius_km),
            "center_lat": round(downstream_lat, 5),
            "center_lon": round(downstream_lon, 5),
            "release_volume_mcm": round(vol_mcm, 2),
            "scenario_name": f"{self.params.dam_name} Release ({int(q_rel)} m³/s for {dur}h)",
        }
