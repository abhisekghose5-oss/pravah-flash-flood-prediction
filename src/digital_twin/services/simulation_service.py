"""
PRAVAH Digital Twin — Simulation Service.
Maintains benchmark scenarios, caches completed runs, and manages simulation state.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from src.digital_twin.models.simulation import (
    AntecedentMoistureCondition,
    SimulationMode,
    SimulationRequest,
    SimulationResult,
)

logger = logging.getLogger("pravah.digital_twin.simulation_service")


class SimulationService:
    """
    Manages benchmark simulation scenarios, execution caches, and parameter validation.
    """

    def __init__(self):
        self.simulation_history: Dict[str, SimulationResult] = {}
        self.preset_scenarios: List[Dict[str, Any]] = [
            {
                "scenario_id": "SCEN_MAHAD_CLOUDBURST",
                "title": "Mahad Savitri Flash Flood / Cloudburst",
                "description": "Extreme convective precipitation event (350 mm in 6 hours) over the steep Western Ghats escarpment.",
                "watershed_id": "INDOFLOODS-gauge-602",
                "rainfall_mm": 350.0,
                "duration_hours": 6.0,
                "antecedent_moisture": "AMC_III",
                "simulation_mode": "COUPLED_HYDROLOGIC",
                "expected_impact": "EXTREME flash flooding, rapid hydrograph peak, severe inundation in low-lying riparian terraces.",
            },
            {
                "scenario_id": "SCEN_KOLHAPUR_2019_MONSOON",
                "title": "Panchganga / Kolhapur 2019 Inundation",
                "description": "Prolonged high-volume monsoon depression (280 mm over 18 hours) causing extensive backwater accumulation.",
                "watershed_id": "INDOFLOODS-gauge-643",
                "rainfall_mm": 280.0,
                "duration_hours": 18.0,
                "antecedent_moisture": "AMC_III",
                "simulation_mode": "COUPLED_HYDROLOGIC",
                "expected_impact": "Widespread backwater flooding, submerged river bridges, prolonged drainage congestion.",
            },
            {
                "scenario_id": "SCEN_BRAHMAPUTRA_SURGE",
                "title": "Brahmaputra / Beki Flash Surge",
                "description": "Torrential Himalayan foothills downpour (180 mm in 8 hours) saturating alluvial floodplain soils.",
                "watershed_id": "NE-Beki",
                "rainfall_mm": 180.0,
                "duration_hours": 8.0,
                "antecedent_moisture": "AMC_II",
                "simulation_mode": "COUPLED_HYDROLOGIC",
                "expected_impact": "High sediment transport, rapid bank erosion, significant low-gradient water accumulation.",
            },
            {
                "scenario_id": "SCEN_KARAD_HIGH_INTENSITY",
                "title": "Krishna / Karad Rapid Convective Storm",
                "description": "High-intensity short-duration storm (120 mm in 3 hours) testing drainage response in volcanic terrain.",
                "watershed_id": "INDOFLOODS-gauge-684",
                "rainfall_mm": 120.0,
                "duration_hours": 3.0,
                "antecedent_moisture": "AMC_II",
                "simulation_mode": "COUPLED_HYDROLOGIC",
                "expected_impact": "Moderate to high flash runoff, localized tributary overflow.",
            },
            {
                "scenario_id": "SCEN_MODERATE_MONSOON",
                "title": "Standard Seasonal Monsoon Showers",
                "description": "Typical monsoon shower event (50 mm in 4 hours) across normal moisture conditions.",
                "watershed_id": "INDOFLOODS-gauge-640",
                "rainfall_mm": 50.0,
                "duration_hours": 4.0,
                "antecedent_moisture": "AMC_I",
                "simulation_mode": "COUPLED_HYDROLOGIC",
                "expected_impact": "Low accumulation, safe river stage below danger thresholds.",
            },
        ]

    def get_preset_scenarios(self) -> List[Dict[str, Any]]:
        """Return library of benchmark scenarios for user exploration."""
        return self.preset_scenarios

    def record_simulation(self, result: SimulationResult) -> None:
        """Store completed simulation in history cache (capped at 50 runs)."""
        self.simulation_history[result.simulation_id] = result
        if len(self.simulation_history) > 50:
            oldest_id = next(iter(self.simulation_history))
            del self.simulation_history[oldest_id]

    def get_simulation_by_id(self, sim_id: str) -> Optional[SimulationResult]:
        """Retrieve historical simulation output by run ID."""
        return self.simulation_history.get(sim_id)
