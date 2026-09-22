"""
PRAVAH Flood Propagation — Simulation Execution & Telemetry Models.
Defines API request and response envelopes for the Flood Propagation Engine.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.simulation.models.scenario import (
    ScenarioType,
    SimulationPeriod,
    RainfallScenarioParams,
    DamReleaseScenarioParams,
    RiverOverflowScenarioParams,
)
from src.simulation.models.inundation import (
    TimeStepInundation,
    ExtentGrowthPoint,
)
from src.simulation.models.impact import (
    TimeStepImpactSummary,
    InfrastructureImpactSummary,
    PopulationExposure,
)


class SimulationRunRequest(BaseModel):
    """Input payload to trigger a time-based flood propagation simulation."""
    scenario_type: ScenarioType = Field(..., description="Scenario category: rainfall, dam_release, river_overflow")
    simulation_period_hours: SimulationPeriod = Field(
        default=SimulationPeriod.PERIOD_24H,
        description="Total simulation horizon: 1, 6, 12, 24, or 48 hours"
    )
    rainfall_params: Optional[RainfallScenarioParams] = Field(
        default=None,
        description="Parameters when scenario_type == 'rainfall'"
    )
    dam_release_params: Optional[DamReleaseScenarioParams] = Field(
        default=None,
        description="Parameters when scenario_type == 'dam_release'"
    )
    river_overflow_params: Optional[RiverOverflowScenarioParams] = Field(
        default=None,
        description="Parameters when scenario_type == 'river_overflow'"
    )


class SimulationRunResponse(BaseModel):
    """Complete results payload returned by the Flood Propagation Engine."""
    simulation_id: str = Field(..., description="Unique simulation run identifier")
    status: str = Field(default="COMPLETED", description="COMPLETED, FAILED, PROCESSING")
    scenario_type: ScenarioType
    scenario_title: str
    target_region: str
    simulation_period_hours: int
    maximum_flood_extent_km2: float = Field(..., description="Peak cumulative inundated area across all steps in km²")
    peak_depth_m: float = Field(..., description="Maximum flood depth across simulation in meters")
    total_population_impacted: int = Field(..., description="Peak population exposed to simulated inundation")
    infrastructure_summary: InfrastructureImpactSummary
    time_steps: List[TimeStepInundation] = Field(default_factory=list, description="Spatial inundation map per time step")
    growth_timeline: List[ExtentGrowthPoint] = Field(default_factory=list, description="Time series of extent growth")
    impact_timeline: List[TimeStepImpactSummary] = Field(default_factory=list, description="Time series of impact metrics")
    provenance_disclaimer: str = Field(
        default="SIMULATED ESTIMATE — Model-derived spatial projections for disaster preparedness. Not observed sensor readings.",
        description="Mandatory advisory notice"
    )
    execution_time_ms: float = Field(default=0.0, description="Processing duration in milliseconds")
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SimulationTimelineResponse(BaseModel):
    """Lightweight timeline payload for quick frontend animation and chart rendering."""
    simulation_id: str
    scenario_type: ScenarioType
    simulation_period_hours: int
    maximum_flood_extent_km2: float
    total_population_impacted: int
    growth_points: List[ExtentGrowthPoint]
    population_points: List[Dict[str, Any]]
    infrastructure_points: List[Dict[str, Any]]


class SimulationHistoryItem(BaseModel):
    """Summary item for historical simulation runs."""
    simulation_id: str
    scenario_type: ScenarioType
    scenario_title: str
    target_region: str
    simulation_period_hours: int
    maximum_flood_extent_km2: float
    total_population_impacted: int
    timestamp_utc: str
