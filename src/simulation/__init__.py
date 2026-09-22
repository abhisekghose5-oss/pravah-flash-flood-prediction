"""
PRAVAH Flood Propagation & Inundation Simulation Engine.
Modular, independent, backward-compatible simulation framework.
"""

from src.simulation.models.scenario import (
    ScenarioType,
    SimulationPeriod,
    SpatialDistribution,
    RainfallScenarioParams,
    DamReleaseScenarioParams,
    RiverOverflowScenarioParams,
    ScenarioTemplate,
)
from src.simulation.models.inundation import (
    DepthCategory,
    FloodSeverityClass,
    InundationDepthStats,
    ExtentGrowthPoint,
    TimeStepInundation,
)
from src.simulation.models.impact import (
    InfrastructureCategory,
    EvacuationUrgency,
    PopulationExposure,
    InfrastructureImpactDetail,
    InfrastructureImpactSummary,
    TimeStepImpactSummary,
)
from src.simulation.models.simulation import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationTimelineResponse,
    SimulationHistoryItem,
)
from src.simulation.inundation_engine import InundationEngine
from src.simulation.impact_engine import ImpactEngine
from src.simulation.time_step_engine import TimeStepEngine
from src.simulation.propagation_engine import FloodPropagationEngine
from src.simulation.scenario_manager import ScenarioManager
from src.simulation.simulation_manager import (
    SimulationManager,
    get_simulation_manager,
)

__all__ = [
    # Enums and Models
    "ScenarioType",
    "SimulationPeriod",
    "SpatialDistribution",
    "RainfallScenarioParams",
    "DamReleaseScenarioParams",
    "RiverOverflowScenarioParams",
    "ScenarioTemplate",
    "DepthCategory",
    "FloodSeverityClass",
    "InundationDepthStats",
    "ExtentGrowthPoint",
    "TimeStepInundation",
    "InfrastructureCategory",
    "EvacuationUrgency",
    "PopulationExposure",
    "InfrastructureImpactDetail",
    "InfrastructureImpactSummary",
    "TimeStepImpactSummary",
    "SimulationRunRequest",
    "SimulationRunResponse",
    "SimulationTimelineResponse",
    "SimulationHistoryItem",
    # Computational Engines
    "InundationEngine",
    "ImpactEngine",
    "TimeStepEngine",
    "FloodPropagationEngine",
    "ScenarioManager",
    "SimulationManager",
    "get_simulation_manager",
]
