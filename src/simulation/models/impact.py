"""
PRAVAH Flood Propagation — Population & Infrastructure Impact Models.
Defines schemas for human exposure, road cutoffs, bridge inundations, and critical facility risks.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InfrastructureCategory(str, Enum):
    """Categorization of physical infrastructure."""
    ROADS = "roads"
    BRIDGES = "bridges"
    HOSPITALS = "hospitals"
    SCHOOLS = "schools"
    CRITICAL_FACILITIES = "critical_facilities"
    POWER_WATER_SITES = "power_water_sites"


class EvacuationUrgency(str, Enum):
    """Urgency level for population in affected zones."""
    MONITORING = "MONITORING"
    ADVISORY = "ADVISORY"
    URGENT = "URGENT"
    MANDATORY = "MANDATORY"


class PopulationExposure(BaseModel):
    """Estimated demographic exposure within simulated inundation boundaries."""
    estimated_population_exposed: int = Field(..., description="Estimated resident population exposed")
    population_density_per_km2: float = Field(default=250.0, description="Average catchment population density")
    high_risk_population: int = Field(default=0, description="Population in severe/extreme depth zones (>1.5m)")
    elderly_and_children_estimate: int = Field(default=0, description="Estimated vulnerable demographic subset")
    evacuation_urgency: EvacuationUrgency = Field(default=EvacuationUrgency.MONITORING)
    data_source_badge: str = Field(
        default="ESTIMATED — LULC Census & Global Human Settlement Layer",
        description="Data provenance notice"
    )


class InfrastructureImpactDetail(BaseModel):
    """A specific affected facility, bridge, or road reach."""
    item_id: str
    name: str
    category: InfrastructureCategory
    status: str = Field(default="SUBMERGED", description="SUBMERGED, CUT_OFF, THREATENED")
    estimated_water_depth_m: float
    latitude: float
    longitude: float


class InfrastructureImpactSummary(BaseModel):
    """Aggregate tally of affected public and emergency infrastructure."""
    submerged_road_segments: int = Field(default=0, description="Number of submerged road reaches")
    submerged_road_length_km: float = Field(default=0.0, description="Total kilometers of inundated roads")
    submerged_bridges: int = Field(default=0, description="Number of submerged or threatened bridges")
    threatened_hospitals: int = Field(default=0, description="Hospitals / medical centers in flood zone")
    threatened_schools: int = Field(default=0, description="Schools / community centers in flood zone")
    threatened_critical_facilities: int = Field(default=0, description="Substations, water pumping, emergency HQ")
    detailed_items: List[InfrastructureImpactDetail] = Field(default_factory=list)


class TimeStepImpactSummary(BaseModel):
    """Consolidated demographic and infrastructural impact at a discrete simulation step."""
    time_step_hours: float
    time_label: str
    population: PopulationExposure
    infrastructure: InfrastructureImpactSummary
