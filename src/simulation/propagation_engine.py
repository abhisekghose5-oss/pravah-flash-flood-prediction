"""
PRAVAH Flood Propagation — Core FloodPropagationEngine.
Orchestrates scenario execution, calls time-step progression, and builds simulation responses.
"""

from datetime import datetime, timezone
import logging
import time
import uuid
from typing import Optional

from src.simulation.models.scenario import ScenarioType
from src.simulation.models.simulation import (
    SimulationRunRequest,
    SimulationRunResponse,
)
from src.simulation.scenarios.rainfall import RainfallScenario
from src.simulation.scenarios.dam_release import DamReleaseScenario
from src.simulation.scenarios.river_overflow import RiverOverflowScenario
from src.simulation.inundation_engine import InundationEngine
from src.simulation.impact_engine import ImpactEngine
from src.simulation.time_step_engine import TimeStepEngine
from src.simulation.services.river_service import RiverService
from src.simulation.services.terrain_service import TerrainService

logger = logging.getLogger("pravah.simulation.propagation")


class FloodPropagationEngine:
    """
    Central computational engine for simulating dynamic time-based flood propagation.
    """

    def __init__(
        self,
        inundation_engine: Optional[InundationEngine] = None,
        impact_engine: Optional[ImpactEngine] = None,
        river_service: Optional[RiverService] = None,
        terrain_service: Optional[TerrainService] = None,
    ):
        self.inundation_engine = inundation_engine or InundationEngine()
        self.impact_engine = impact_engine or ImpactEngine()
        self.river_service = river_service or RiverService()
        self.terrain_service = terrain_service or TerrainService()
        self.time_step_engine = TimeStepEngine(self.inundation_engine, self.impact_engine)

    def execute_simulation(self, request: SimulationRunRequest) -> SimulationRunResponse:
        """
        Execute full flood propagation run across discrete time steps.
        """
        start_time = time.time()
        sim_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"
        period_hours = int(request.simulation_period_hours)

        # ---------------------------------------------------------------------
        # 1. Dispatch Scenario
        # ---------------------------------------------------------------------
        if request.scenario_type == ScenarioType.RAINFALL:
            if not request.rainfall_params:
                raise ValueError("Missing rainfall_params for RAINFALL scenario")

            params = request.rainfall_params
            scen_calc = RainfallScenario(params)
            catchment_id = params.catchment_id
            terrain = self.terrain_service.get_terrain_profile(catchment_id)
            centroid = terrain["centroid"]
            scenario_title = f"Heavy Rainfall ({params.rainfall_mm}mm / {params.rainfall_duration_hours}h)"
            target_region = f"Catchment {catchment_id} (Western Ghats)"

            def step_calc(t: float):
                return scen_calc.compute_propagation(
                    elapsed_hours=t,
                    total_period_hours=period_hours,
                    centroid=centroid,
                )

        elif request.scenario_type == ScenarioType.DAM_RELEASE:
            if not request.dam_release_params:
                raise ValueError("Missing dam_release_params for DAM_RELEASE scenario")

            params = request.dam_release_params
            scen_calc = DamReleaseScenario(params)
            dam_info = self.river_service.get_dam(params.dam_id)
            if not dam_info:
                # Default to Koyna Dam coordinates
                dam_info = {
                    "lat": 17.4000,
                    "lon": 73.7500,
                    "downstream_catchment_id": "INDOFLOODS-gauge-684",
                    "name": params.dam_name or "Regional Reservoir",
                }

            catchment_id = dam_info.get("downstream_catchment_id", "INDOFLOODS-gauge-684")
            dam_coords = (dam_info["lat"], dam_info["lon"])
            scenario_title = f"{params.dam_name} Discharge ({int(params.release_rate_m3s)} m³/s)"
            target_region = f"{params.river_basin} River Basin ({dam_info['name']})"

            def step_calc(t: float):
                return scen_calc.compute_propagation(
                    elapsed_hours=t,
                    total_period_hours=period_hours,
                    dam_coords=dam_coords,
                )

        elif request.scenario_type == ScenarioType.RIVER_OVERFLOW:
            if not request.river_overflow_params:
                raise ValueError("Missing river_overflow_params for RIVER_OVERFLOW scenario")

            params = request.river_overflow_params
            scen_calc = RiverOverflowScenario(params)
            river_info = self.river_service.get_river(params.river_id)
            if not river_info:
                # Default to Savitri River (Mahad) coordinates
                river_info = {
                    "lat": 18.0922,
                    "lon": 73.4603,
                    "gauge_id": params.gauge_id or "INDOFLOODS-gauge-602",
                    "name": params.river_name or "Riparian River Reach",
                    "basin": "Western Ghats Corridor",
                }

            catchment_id = river_info.get("gauge_id", "INDOFLOODS-gauge-602")
            river_coords = (river_info["lat"], river_info["lon"])
            diff = params.simulated_water_level_m - params.overflow_threshold_m
            scenario_title = f"{params.river_name} Cresting (+{round(diff, 1)}m Stage Breach)"
            target_region = f"{river_info.get('basin', 'Basin')} — {river_info['name']}"

            def step_calc(t: float):
                return scen_calc.compute_propagation(
                    elapsed_hours=t,
                    total_period_hours=period_hours,
                    river_coords=river_coords,
                )

        else:
            raise ValueError(f"Unsupported scenario_type: {request.scenario_type}")

        # ---------------------------------------------------------------------
        # 2. Advance Simulation Through Temporal Time Steps
        # ---------------------------------------------------------------------
        (
            time_steps,
            growth_timeline,
            impact_timeline,
            max_extent,
            peak_depth,
        ) = self.time_step_engine.advance_simulation(
            period_hours=period_hours,
            catchment_id=catchment_id,
            step_calculator_fn=step_calc,
        )

        # ---------------------------------------------------------------------
        # 3. Aggregate Peak Metrics Across Steps
        # ---------------------------------------------------------------------
        max_pop = max((step.population.estimated_population_exposed for step in impact_timeline), default=0)
        final_infra = impact_timeline[-1].infrastructure if impact_timeline else None

        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)

        return SimulationRunResponse(
            simulation_id=sim_id,
            status="COMPLETED",
            scenario_type=request.scenario_type,
            scenario_title=scenario_title,
            target_region=target_region,
            simulation_period_hours=period_hours,
            maximum_flood_extent_km2=max_extent,
            peak_depth_m=peak_depth,
            total_population_impacted=max_pop,
            infrastructure_summary=final_infra,
            time_steps=time_steps,
            growth_timeline=growth_timeline,
            impact_timeline=impact_timeline,
            provenance_disclaimer="SIMULATED ESTIMATE — Model-derived spatial projections for disaster preparedness. Not observed sensor readings.",
            execution_time_ms=elapsed_ms,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )
