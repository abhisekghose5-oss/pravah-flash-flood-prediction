"""
PRAVAH Flood Propagation — Temporal Time-Step Progression Engine.
Advances the flood simulation through discrete temporal steps (0h, 1h, 6h, 12h, 24h, 48h),
generating spatial maps, growth rates, and impact time series.
"""

from typing import Any, Callable, Dict, List, Tuple

from src.simulation.models.inundation import (
    ExtentGrowthPoint,
    TimeStepInundation,
)
from src.simulation.models.impact import TimeStepImpactSummary
from src.simulation.inundation_engine import InundationEngine
from src.simulation.impact_engine import ImpactEngine
from src.simulation.utils.simulation_utils import get_discrete_time_steps


class TimeStepEngine:
    """
    Executes time-stepping progression, advancing propagation metrics
    and producing synchronized maps and impact time series.
    """

    def __init__(
        self,
        inundation_engine: InundationEngine,
        impact_engine: ImpactEngine
    ):
        self.inundation_engine = inundation_engine
        self.impact_engine = impact_engine

    def advance_simulation(
        self,
        period_hours: int,
        catchment_id: str,
        step_calculator_fn: Callable[[float], Dict[str, Any]],
    ) -> Tuple[List[TimeStepInundation], List[ExtentGrowthPoint], List[TimeStepImpactSummary], float, float]:
        """
        Advance simulation through time steps corresponding to the chosen horizon.
        """
        steps = get_discrete_time_steps(period_hours)

        time_steps: List[TimeStepInundation] = []
        growth_timeline: List[ExtentGrowthPoint] = []
        impact_timeline: List[TimeStepImpactSummary] = []

        max_extent_observed = 0.0
        peak_depth_observed = 0.0
        prev_area = 0.0

        for t in steps:
            time_label = f"T+{int(t)}h" if t.is_integer() else f"T+{t:.1f}h"

            # 1. Compute scenario-specific hydraulic propagation at time t
            step_data = step_calculator_fn(t)
            flooded_area = float(step_data["flooded_area_km2"])
            radius_km = float(step_data["flood_radius_km"])
            peak_depth = float(step_data["peak_depth_m"])
            c_lat = float(step_data["center_lat"])
            c_lon = float(step_data["center_lon"])

            max_extent_observed = max(max_extent_observed, flooded_area)
            peak_depth_observed = max(peak_depth_observed, peak_depth)

            # Growth rate calculation: (Current - Prev) / Prev * 100
            if prev_area > 0.01:
                growth_rate = round(((flooded_area - prev_area) / prev_area) * 100.0, 1)
            elif flooded_area > 0.01:
                growth_rate = 100.0
            else:
                growth_rate = 0.0
            prev_area = flooded_area

            # 2. Record extent growth time series point
            growth_timeline.append(
                ExtentGrowthPoint(
                    time_hours=t,
                    time_label=time_label,
                    flooded_area_km2=flooded_area,
                    growth_rate_pct=growth_rate,
                    peak_depth_m=peak_depth,
                )
            )

            # 3. Generate spatial inundation polygon layer for this step
            inundation_step = self.inundation_engine.generate_timestep_inundation(
                time_hours=t,
                time_label=time_label,
                center_lat=c_lat,
                center_lon=c_lon,
                flood_radius_km=radius_km,
                flooded_area_km2=flooded_area,
                peak_depth_m=peak_depth,
            )
            time_steps.append(inundation_step)

            # 4. Generate demographic and infrastructure impact for this step
            impact_step = self.impact_engine.evaluate_step_impact(
                time_hours=t,
                time_label=time_label,
                catchment_id=catchment_id,
                center_lat=c_lat,
                center_lon=c_lon,
                flooded_area_km2=flooded_area,
                flood_radius_km=radius_km,
                peak_depth_m=peak_depth,
            )
            impact_timeline.append(impact_step)

        return (
            time_steps,
            growth_timeline,
            impact_timeline,
            round(max_extent_observed, 2),
            round(peak_depth_observed, 2)
        )
