"""
PRAVAH Digital Twin — Terrain & DEM Models.
Defines schemas for Digital Elevation Models, topographic gradients, slope, and aspect.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ElevationStats(BaseModel):
    """Statistical summary of terrain elevation across a watershed."""
    min_elevation_m: float = Field(..., description="Minimum elevation (m MSL)")
    max_elevation_m: float = Field(..., description="Maximum elevation (m MSL)")
    mean_elevation_m: float = Field(..., description="Mean elevation (m MSL)")
    elevation_range_m: float = Field(..., description="Topographic relief (max - min) in meters")


class SlopeStats(BaseModel):
    """Statistical summary of terrain slope gradients."""
    min_slope_deg: float = Field(default=0.0, description="Minimum surface slope (degrees)")
    max_slope_deg: float = Field(..., description="Maximum surface slope (degrees)")
    mean_slope_deg: float = Field(..., description="Mean surface slope (degrees)")
    steep_terrain_pct: float = Field(default=0.0, description="Percentage of catchment with slope > 15 degrees")


class AspectDistribution(BaseModel):
    """Fractional distribution of terrain aspect directions (N, NE, E, SE, S, SW, W, NW, Flat)."""
    north_pct: float = Field(default=12.5)
    northeast_pct: float = Field(default=12.5)
    east_pct: float = Field(default=12.5)
    southeast_pct: float = Field(default=12.5)
    south_pct: float = Field(default=12.5)
    southwest_pct: float = Field(default=12.5)
    west_pct: float = Field(default=12.5)
    northwest_pct: float = Field(default=12.5)
    predominant_direction: str = Field(default="East", description="Predominant facing aspect")


class DEMGridMetadata(BaseModel):
    """Spatial reference and raster grid resolution for DEM processing."""
    rows: int = Field(..., description="Number of raster grid rows")
    cols: int = Field(..., description="Number of raster grid columns")
    cell_size_deg: float = Field(default=0.01, description="Grid resolution in decimal degrees")
    crs: str = Field(default="EPSG:4326", description="Coordinate reference system")
    bounds: List[float] = Field(..., description="[west_lon, south_lat, east_lon, north_lat]")


class TerrainModelOutput(BaseModel):
    """Complete terrain characterization payload for visualization in the Digital Twin."""
    watershed_id: str
    grid_metadata: DEMGridMetadata
    elevation: ElevationStats
    slope: SlopeStats
    aspect: AspectDistribution
    contour_intervals: List[float] = Field(default_factory=list, description="Elevations for contour isolines")
    hypsometric_bands: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Hypsometric color intervals [{min_elev, max_elev, color, label}]"
    )
    flow_direction_algorithm: str = Field(default="D8_deterministic", description="D8 flow direction algorithm")
