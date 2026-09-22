"""
PRAVAH Flood Propagation — Central SimulationManager.
Singleton orchestrator coordinating scenario management, execution, result caching,
and multi-tier query lookups.
"""

from collections import OrderedDict
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import threading

from src.simulation.models.scenario import ScenarioTemplate
from src.simulation.models.simulation import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationTimelineResponse,
    SimulationHistoryItem,
)
from src.simulation.propagation_engine import FloodPropagationEngine
from src.simulation.scenario_manager import ScenarioManager

logger = logging.getLogger("pravah.simulation.manager")


class SimulationManager:
    """
    Central coordinator and in-memory cache for all simulation runs in PRAVAH.
    Thread-safe singleton orchestrator.
    """

    MAX_CACHE_SIZE = 50

    def __init__(
        self,
        propagation_engine: Optional[FloodPropagationEngine] = None,
        scenario_manager: Optional[ScenarioManager] = None,
    ):
        self.propagation_engine = propagation_engine or FloodPropagationEngine()
        self.scenario_manager = scenario_manager or ScenarioManager()
        self._simulations: OrderedDict[str, SimulationRunResponse] = OrderedDict()
        self._lock = threading.Lock()
        logger.info("SimulationManager initialized with engine and scenario registry")

    def run_simulation(self, request: SimulationRunRequest) -> SimulationRunResponse:
        """
        Execute a flood propagation simulation and cache the results.
        """
        result = self.propagation_engine.execute_simulation(request)
        with self._lock:
            self._simulations[result.simulation_id] = result
            # Maintain cache size limit
            while len(self._simulations) > self.MAX_CACHE_SIZE:
                self._simulations.popitem(last=False)

        logger.info(
            "Executed simulation %s: %s | max extent: %.2f km² | pop: %d",
            result.simulation_id,
            result.scenario_title,
            result.maximum_flood_extent_km2,
            result.total_population_impacted,
        )
        return result

    def get_simulation(self, simulation_id: str) -> Optional[SimulationRunResponse]:
        """
        Retrieve a simulation run by ID.
        """
        with self._lock:
            return self._simulations.get(simulation_id)

    def get_simulation_inundation(
        self, simulation_id: str, time_step_hour: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve spatial inundation GeoJSON and depth layers for a simulation,
        optionally filtered to a specific elapsed hour step.
        """
        sim = self.get_simulation(simulation_id)
        if not sim:
            return None

        if time_step_hour is not None:
            # Find closest matching time step
            step = min(sim.time_steps, key=lambda s: abs(s.time_step_hours - time_step_hour))
            return {
                "simulation_id": sim.simulation_id,
                "time_step_hours": step.time_step_hours,
                "time_label": step.time_label,
                "total_extent_km2": step.total_extent_km2,
                "depth_stats": step.depth_stats.model_dump(),
                "severity_breakdown_km2": step.severity_breakdown_km2,
                "geojson": step.geojson_feature_collection,
            }

        return {
            "simulation_id": sim.simulation_id,
            "total_steps": len(sim.time_steps),
            "time_steps": [
                {
                    "time_step_hours": s.time_step_hours,
                    "time_label": s.time_label,
                    "total_extent_km2": s.total_extent_km2,
                    "depth_stats": s.depth_stats.model_dump(),
                    "severity_breakdown_km2": s.severity_breakdown_km2,
                    "geojson": s.geojson_feature_collection,
                }
                for s in sim.time_steps
            ],
        }

    def get_population_impact(
        self, simulation_id: str, time_step_hour: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve population exposure metrics, optionally at a specific elapsed hour.
        """
        sim = self.get_simulation(simulation_id)
        if not sim:
            return None

        if time_step_hour is not None:
            step_impact = min(
                sim.impact_timeline,
                key=lambda s: abs(s.time_step_hours - time_step_hour),
            )
            return {
                "simulation_id": sim.simulation_id,
                "time_step_hours": step_impact.time_step_hours,
                "population_exposure": step_impact.population.model_dump(),
            }

        return {
            "simulation_id": sim.simulation_id,
            "peak_population_exposed": sim.total_population_impacted,
            "timeline": [
                {
                    "time_step_hours": item.time_step_hours,
                    "time_label": item.time_label,
                    "population": item.population.model_dump(),
                }
                for item in sim.impact_timeline
            ],
        }

    def get_infrastructure_impact(
        self, simulation_id: str, time_step_hour: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve lifeline infrastructure impact assessment.
        """
        sim = self.get_simulation(simulation_id)
        if not sim:
            return None

        if time_step_hour is not None:
            step_impact = min(
                sim.impact_timeline,
                key=lambda s: abs(s.time_step_hours - time_step_hour),
            )
            return {
                "simulation_id": sim.simulation_id,
                "time_step_hours": step_impact.time_step_hours,
                "infrastructure_impact": step_impact.infrastructure.model_dump(),
            }

        return {
            "simulation_id": sim.simulation_id,
            "final_summary": sim.infrastructure_summary.model_dump(),
            "timeline": [
                {
                    "time_step_hours": item.time_step_hours,
                    "time_label": item.time_label,
                    "infrastructure": item.infrastructure.model_dump(),
                }
                for item in sim.impact_timeline
            ],
        }

    def get_timeline(self, simulation_id: str) -> Optional[SimulationTimelineResponse]:
        """
        Extract simplified time series suitable for instant graph visualization.
        """
        sim = self.get_simulation(simulation_id)
        if not sim:
            return None

        population_points = [
            {
                "time_step_hours": pt.time_step_hours,
                "time_label": pt.time_label,
                "estimated_population_exposed": pt.population.estimated_population_exposed,
                "high_risk_population": pt.population.high_risk_population,
                "elderly_and_children_estimate": pt.population.elderly_and_children_estimate,
            }
            for pt in sim.impact_timeline
        ]

        infra_points = [
            {
                "time_step_hours": pt.time_step_hours,
                "time_label": pt.time_label,
                "submerged_road_length_km": pt.infrastructure.submerged_road_length_km,
                "submerged_bridges": pt.infrastructure.submerged_bridges,
                "threatened_hospitals": pt.infrastructure.threatened_hospitals,
                "threatened_schools": pt.infrastructure.threatened_schools,
                "threatened_critical_facilities": pt.infrastructure.threatened_critical_facilities,
            }
            for pt in sim.impact_timeline
        ]

        return SimulationTimelineResponse(
            simulation_id=sim.simulation_id,
            scenario_type=sim.scenario_type,
            simulation_period_hours=sim.simulation_period_hours,
            maximum_flood_extent_km2=sim.maximum_flood_extent_km2,
            total_population_impacted=sim.total_population_impacted,
            growth_points=sim.growth_timeline,
            population_points=population_points,
            infrastructure_points=infra_points,
        )

    def list_history(self, limit: int = 20) -> List[SimulationHistoryItem]:
        """
        Retrieve recent simulation run history items.
        """
        with self._lock:
            items = list(self._simulations.values())

        # Sort reverse chronological
        items = sorted(items, key=lambda x: x.timestamp_utc, reverse=True)[:limit]
        return [
            SimulationHistoryItem(
                simulation_id=x.simulation_id,
                scenario_type=x.scenario_type,
                scenario_title=x.scenario_title,
                target_region=x.target_region,
                simulation_period_hours=x.simulation_period_hours,
                maximum_flood_extent_km2=x.maximum_flood_extent_km2,
                total_population_impacted=x.total_population_impacted,
                timestamp_utc=x.timestamp_utc,
            )
            for x in items
        ]

    def cancel_simulation(self, simulation_id: str) -> bool:
        """
        Cancel a running or scheduled simulation run.
        """
        with self._lock:
            if simulation_id in self._simulations:
                sim = self._simulations[simulation_id]
                if sim.status not in ("COMPLETED", "FAILED"):
                    sim.status = "CANCELLED"
                    return True
        return False

    def get_scenario_templates(self) -> List[ScenarioTemplate]:
        """
        List pre-configured benchmark scenario presets.
        """
        return self.scenario_manager.list_scenarios()

    def get_status(self) -> Dict[str, Any]:
        """
        Status and health diagnostics of the flood propagation engine.
        """
        rivers = self.propagation_engine.river_service.list_rivers()
        dams = self.propagation_engine.river_service.list_dams()
        return {
            "status": "OPERATIONAL",
            "service": "PRAVAH Flood Propagation & Inundation Simulation Engine",
            "version": "1.0.0",
            "active_simulations_cached": len(self._simulations),
            "supported_scenarios": ["rainfall", "dam_release", "river_overflow"],
            "supported_periods_hours": [1, 6, 12, 24, 48],
            "depth_classifications_m": ["0.0-0.5", "0.5-1.0", "1.0-2.0", "2.0-5.0", ">5.0"],
            "monitored_rivers": [r["name"] for r in rivers],
            "monitored_dams": [d["name"] for d in dams],
            "demographic_data_loaded": self.propagation_engine.impact_engine.population_service.is_loaded(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }


# Singleton accessor
_manager_instance: Optional[SimulationManager] = None
_manager_lock = threading.Lock()


def get_simulation_manager() -> SimulationManager:
    """
    Get or initialize the global singleton SimulationManager.
    """
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = SimulationManager()
    return _manager_instance
