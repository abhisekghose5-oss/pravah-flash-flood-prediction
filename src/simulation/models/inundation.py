"""
PRAVAH Flood Propagation — Inundation Depth & Extent Models.
Defines schemas for water depth intervals, severity classifications, and spatial flood footprints.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DepthCategory(str, Enum):
    """Standardized floodwater depth intervals."""
    SHALLOW_0_05M = "0-0.5m"      # Minor ankle-depth inundation
    MODERATE_05_1M = "0.5-1.0m"   # Knee/waist-depth, impassable for cars
    DEEP_1_2M = "1.0-2.0m"        # Chest-depth, structural inundation
    SEVERE_2_5M = "2.0-5.0m"      # Submerged single-story dwellings
    EXTREME_GT_5M = ">5.0m"       # Catastrophic multi-story inundation


class FloodSeverityClass(str, Enum):
    """Categorical hazard severity classification."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"
    EXTREME = "EXTREME"


class InundationDepthStats(BaseModel):
    """Statistical summary of flood depths across the inundated zone."""
    min_depth_m: float = Field(default=0.1, description="Minimum flood depth in meters")
    max_depth_m: float = Field(..., description="Maximum peak flood depth in meters")
    mean_depth_m: float = Field(..., description="Average flood depth across inundated area in meters")
    predominant_category: DepthCategory = Field(default=DepthCategory.MODERATE_05_1M)


class ExtentGrowthPoint(BaseModel):
    """A discrete temporal data point tracking flood footprint growth."""
    time_hours: float = Field(..., description="Elapsed simulation time in hours")
    time_label: str = Field(..., description="Formatted step label (e.g. 'T+6h')")
    flooded_area_km2: float = Field(..., description="Total inundated footprint in km²")
    growth_rate_pct: float = Field(default=0.0, description="Percentage change in area since previous time step")
    peak_depth_m: float = Field(..., description="Peak depth recorded at this step")


class TimeStepInundation(BaseModel):
    """Complete spatial inundation state for a discrete simulation time step."""
    time_step_hours: float = Field(..., description="Elapsed simulation time in hours (0, 1, 6, 12, 24, 48)")
    time_label: str = Field(..., description="Formatted step label (e.g. 'T+12h')")
    total_extent_km2: float = Field(..., description="Total flooded area in km²")
    depth_stats: InundationDepthStats
    severity_breakdown_km2: Dict[str, float] = Field(
        default_factory=dict,
        description="Area breakdown by severity: {'LOW': km², 'MODERATE': km², 'HIGH': km², 'SEVERE': km², 'EXTREME': km²}"
    )
    geojson_feature_collection: Dict[str, Any] = Field(
        ...,
        description="GeoJSON FeatureCollection representing inundation polygons at this step"
    )
