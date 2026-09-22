"""
PRAVAH Digital Twin — River Basin Models.
Defines schemas for river basins, stream reaches, stream order networks, and drainage hierarchy.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RiverSegment(BaseModel):
    """A discrete channel reach or river segment."""
    segment_id: str = Field(..., description="Unique river reach identifier")
    river_name: str = Field(..., description="Name of river or tributary reach")
    stream_order: int = Field(default=1, description="Strahler stream order (1-5)")
    length_km: float = Field(..., description="Length of river segment in kilometers")
    slope_gradient: float = Field(default=0.005, description="Channel bed gradient (m/m)")
    downstream_segment_id: Optional[str] = Field(default=None, description="Downstream connecting segment ID")
    coordinates: List[List[float]] = Field(
        ...,
        description="LineString coordinates [[lon, lat], [lon, lat], ...]"
    )


class RiverBasinSummary(BaseModel):
    """High-level basin properties and monitoring stations."""
    basin_id: str = Field(..., description="Basin code (e.g. BASIN_KRISHNA, BASIN_BRAHMAPUTRA)")
    basin_name: str = Field(..., description="Basin name (e.g. Krishna, Savitri, Brahmaputra)")
    region: str = Field(..., description="Region (e.g. Maharashtra Western Ghats, Northeast India)")
    total_area_sqkm: float = Field(..., description="Total catchment drainage area in km²")
    main_rivers: List[str] = Field(default_factory=list, description="Primary rivers in the basin")
    tributaries: List[str] = Field(default_factory=list, description="Major tributary streams")
    station_count: int = Field(default=1, description="Number of monitoring gauges in basin")
    active_watersheds: List[str] = Field(default_factory=list, description="Watershed IDs in basin")


class RiverBasinNetwork(BaseModel):
    """Complete basin river network with GeoJSON representation and segment details."""
    basin: RiverBasinSummary
    segments: List[RiverSegment]
    geojson_feature_collection: Dict[str, Any] = Field(
        ...,
        description="GeoJSON FeatureCollection containing all LineString stream reaches"
    )
