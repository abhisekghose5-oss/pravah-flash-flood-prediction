"""
PRAVAH Flood Propagation — Scenario Manager.
Curates benchmark scenario presets for Rainfall, Dam Releases, and River Overflows.
"""

from typing import Any, Dict, List, Optional
from src.simulation.models.scenario import (
    ScenarioType,
    SimulationPeriod,
    ScenarioTemplate,
)


class ScenarioManager:
    """
    Registry of pre-configured scenario templates for operators and judges.
    """

    def __init__(self):
        self.templates: List[ScenarioTemplate] = [
            ScenarioTemplate(
                template_id="SCEN_RAINFALL_MAHAD",
                scenario_type=ScenarioType.RAINFALL,
                title="Mahad Savitri Flash Downpour",
                description="Simulates 220 mm intense convective deluge over the steep Konkan escarpment.",
                region="Savitri River Basin (Maharashtra)",
                default_period_hours=SimulationPeriod.PERIOD_24H,
                parameters={
                    "rainfall_mm": 220.0,
                    "rainfall_duration_hours": 6.0,
                    "spatial_distribution": "convective_core",
                    "catchment_id": "INDOFLOODS-gauge-602",
                    "initial_soil_saturation_pct": 80.0,
                },
            ),
            ScenarioTemplate(
                template_id="SCEN_DAM_KOYNA_RELEASE",
                scenario_type=ScenarioType.DAM_RELEASE,
                title="Koyna Dam Controlled Spillway Release",
                description="High-volume emergency reservoir release (4,500 m³/s for 4 hours) into the upper Krishna corridor.",
                region="Krishna / Koyna Valley (Satara / Karad)",
                default_period_hours=SimulationPeriod.PERIOD_24H,
                parameters={
                    "dam_id": "DAM_KOYNA",
                    "dam_name": "Koyna Dam",
                    "river_basin": "Krishna",
                    "release_rate_m3s": 4500.0,
                    "release_duration_hours": 4.0,
                    "downstream_safe_capacity_m3s": 2500.0,
                    "reservoir_level_pct": 95.0,
                },
            ),
            ScenarioTemplate(
                template_id="SCEN_OVERFLOW_SAVITRI",
                scenario_type=ScenarioType.RIVER_OVERFLOW,
                title="Savitri River Lowland Bank Breach",
                description="River stage rises to 12.6m (1.6m above danger threshold), spilling into Gandhari floodplain.",
                region="Mahad Floodplain (Raigad)",
                default_period_hours=SimulationPeriod.PERIOD_12H,
                parameters={
                    "river_id": "RIVER_SAVITRI",
                    "river_name": "Savitri River",
                    "gauge_id": "INDOFLOODS-gauge-602",
                    "initial_water_level_m": 10.2,
                    "overflow_threshold_m": 11.0,
                    "simulated_water_level_m": 12.6,
                    "duration_hours": 8.0,
                    "breach_width_m": 60.0,
                },
            ),
            ScenarioTemplate(
                template_id="SCEN_DAM_UJANI_SURGE",
                scenario_type=ScenarioType.DAM_RELEASE,
                title="Ujani Dam Monsoon Discharge Wave",
                description="Sustained spillway outflow of 6,200 m³/s over 6 hours traversing the Bhima agricultural basin.",
                region="Bhima River Basin (Solapur / Pune)",
                default_period_hours=SimulationPeriod.PERIOD_48H,
                parameters={
                    "dam_id": "DAM_UJANI",
                    "dam_name": "Ujani Dam",
                    "river_basin": "Krishna",
                    "release_rate_m3s": 6200.0,
                    "release_duration_hours": 6.0,
                    "downstream_safe_capacity_m3s": 3000.0,
                    "reservoir_level_pct": 98.0,
                },
            ),
            ScenarioTemplate(
                template_id="SCEN_OVERFLOW_PANCHGANGA",
                scenario_type=ScenarioType.RIVER_OVERFLOW,
                title="Panchganga River Kolhapur Overtopping",
                description="Panchganga crests at 537.8m (1.8m above danger mark), threatening Kolhapur bridges.",
                region="Panchganga Basin (Kolhapur)",
                default_period_hours=SimulationPeriod.PERIOD_24H,
                parameters={
                    "river_id": "RIVER_PANCHGANGA",
                    "river_name": "Panchganga River",
                    "gauge_id": "INDOFLOODS-gauge-643",
                    "initial_water_level_m": 535.0,
                    "overflow_threshold_m": 536.0,
                    "simulated_water_level_m": 537.8,
                    "duration_hours": 12.0,
                    "breach_width_m": 85.0,
                },
            ),
        ]

    def list_templates(self) -> List[ScenarioTemplate]:
        return self.templates

    def list_scenarios(self) -> List[ScenarioTemplate]:
        return self.templates

    def get_template(self, template_id: str) -> Optional[ScenarioTemplate]:
        for t in self.templates:
            if t.template_id == template_id:
                return t
        return None
