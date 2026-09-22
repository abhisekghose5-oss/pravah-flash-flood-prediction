"""
PRAVAH Digital Twin — Watershed Data Models.
Defines schemas for watersheds, sub-catchments, boundaries, and hydrologic attributes.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SubWatershed(BaseModel):
    """Sub-catchment drainage unit within a primary watershed."""
    sub_id: str = Field(..., description="Unique sub-basin identifier")
    name: str = Field(..., description="Sub-basin or tributary name")
    drainage_area_sqkm: float = Field(..., description="Drainage area in square kilometers")
    stream_order: int = Field(default=1, description="Strahler stream order")
    mean_elevation_m: float = Field(default=0.0, description="Mean surface elevation in meters")
    slope_deg: float = Field(default=0.0, description="Mean surface slope in degrees")
    flow_destination_id: Optional[str] = Field(default=None, description="Downstream receiving sub-basin ID")


class WatershedProperties(BaseModel):
    """Hydrological and geospatial metadata for a monitored catchment."""
    watershed_id: str = Field(..., description="Standardized gauge or catchment identifier")
    gauge_id: Optional[str] = Field(default=None, description="INDOFLOODS or CWC gauge ID")
    station_name: str = Field(..., description="Primary monitoring station name")
    river_name: str = Field(..., description="River, tributary, or stream name")
    basin_name: str = Field(..., description="Primary river basin (e.g. Krishna, Brahmaputra)")
    state: str = Field(default="Maharashtra", description="State or administrative region")
    drainage_area_sqkm: float = Field(..., description="Total watershed area in km²")
    perimeter_km: float = Field(default=0.0, description="Catchment perimeter in km")
    relief_m: float = Field(default=0.0, description="Total catchment relief (elevation delta) in meters")
    mean_elevation_m: float = Field(default=0.0, description="Average terrain elevation in meters")
    max_flow_length_km: float = Field(default=0.0, description="Maximal flow length in km")
    stream_order: int = Field(default=3, description="Highest Strahler stream order")
    drainage_density: float = Field(default=0.0, description="Drainage network density in km/km²")
    soil_type: str = Field(default="Vertisols", description="Dominant soil classification")
    land_cover: str = Field(default="Cropland", description="Dominant land use / land cover")
    curve_number_amc2: float = Field(default=75.0, description="SCS Runoff Curve Number (AMC II)")
    time_of_concentration_hr: float = Field(default=4.5, description="Time of concentration in hours")
    warning_level_m: Optional[float] = Field(default=None, description="Stage warning level in meters")
    danger_level_m: Optional[float] = Field(default=None, description="Stage danger level in meters")
    centroid_lat: float = Field(..., description="Watershed centroid latitude")
    centroid_lon: float = Field(..., description="Watershed centroid longitude")
    bbox: List[float] = Field(default_factory=list, description="[min_lon, min_lat, max_lon, max_lat]")


class Watershed(BaseModel):
    """Complete watershed entity including GeoJSON geometry and sub-basins."""
    id: str
    properties: WatershedProperties
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry object (Polygon or MultiPolygon)")
    sub_watersheds: List[SubWatershed] = Field(default_factory=list)


class WatershedListResponse(BaseModel):
    """API payload response for listing available watersheds in Digital Twin."""
    count: int
    watersheds: List[WatershedProperties]
    geojson_feature_collection: Optional[Dict[str, Any]] = None
