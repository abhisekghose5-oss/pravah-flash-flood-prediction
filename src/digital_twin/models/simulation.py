"""
PRAVAH Digital Twin — Hydrological Simulation Request & Response Models.
Defines schemas for simulation parameters, SCS-CN runoff, water accumulation, and particle paths.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class AntecedentMoistureCondition(str, Enum):
    """Antecedent Moisture Condition (AMC) for SCS Curve Number adjustments."""
    AMC_I = "AMC_I"       # Dry soil (low runoff)
    AMC_II = "AMC_II"     # Average soil condition
    AMC_III = "AMC_III"   # Wet / saturated soil (high runoff)

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().upper().replace("-", "_").replace(" ", "_")
            if clean in ("I", "1", "DRY"):
                return cls.AMC_I
            if clean in ("II", "2", "AVG", "AVERAGE"):
                return cls.AMC_II
            if clean in ("III", "3", "WET", "SATURATED"):
                return cls.AMC_III
            for member in cls:
                if member.value == clean or member.name == clean:
                    return member
        return None


class SimulationMode(str, Enum):
    """Hydrological simulation mode."""
    RUNOFF_ONLY = "RUNOFF_ONLY"
    ACCUMULATION_ONLY = "ACCUMULATION_ONLY"
    COUPLED_HYDROLOGIC = "COUPLED_HYDROLOGIC"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().upper().replace("-", "_").replace(" ", "_")
            for member in cls:
                if member.value == clean or member.name == clean:
                    return member
        return None


class AccumulationSeverity(str, Enum):
    """Severity classification for water accumulation zones."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().upper().replace("-", "_").replace(" ", "_")
            for member in cls:
                if member.value == clean or member.name == clean:
                    return member
        return None


class SimulationRequest(BaseModel):
    """Incoming parameter payload to trigger a digital twin hydrological simulation."""
    watershed_id: str = Field(..., description="Target watershed or catchment ID")
    rainfall_mm: float = Field(..., ge=1.0, le=1000.0, description="Total cumulative precipitation in millimeters")
    duration_hours: float = Field(default=3.0, ge=0.5, le=72.0, description="Rainfall storm duration in hours")
    antecedent_moisture: AntecedentMoistureCondition = Field(
        default=AntecedentMoistureCondition.AMC_II,
        description="Antecedent moisture condition (AMC_I, AMC_II, AMC_III)"
    )
    simulation_mode: SimulationMode = Field(
        default=SimulationMode.COUPLED_HYDROLOGIC,
        description="Simulation calculation mode"
    )
    time_step_mins: int = Field(default=15, ge=5, le=60, description="Simulation time-step granularity in minutes")

    @model_validator(mode='before')
    @classmethod
    def check_simulation_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "watershed_id" not in d or not d["watershed_id"]:
                w = d.get("watershed") or d.get("catchment_id") or d.get("basin_id")
                if w:
                    d["watershed_id"] = str(w)
            if "rainfall_mm" not in d or d["rainfall_mm"] is None:
                for k in ("rainfall", "rainfall_intensity", "precipitation_mm", "rain_mm"):
                    if k in d and d[k] is not None:
                        d["rainfall_mm"] = float(d[k])
                        break
            return d
        return data


class RunoffSummary(BaseModel):
    """Hydrological runoff metrics derived from SCS Curve Number modeling."""
    curve_number_applied: float = Field(..., description="Effective SCS Curve Number used")
    potential_retention_s_mm: float = Field(..., description="Potential maximum soil retention S (mm)")
    initial_abstraction_ia_mm: float = Field(..., description="Initial abstraction Ia = 0.2 * S (mm)")
    effective_rainfall_p_mm: float = Field(..., description="Gross rainfall input P (mm)")
    direct_runoff_depth_mm: float = Field(..., description="Direct runoff depth Q (mm)")
    runoff_coefficient: float = Field(..., description="Volumetric runoff ratio Q / P (0.0 to 1.0)")
    total_runoff_volume_m3: float = Field(..., description="Total volumetric discharge in cubic meters")
    total_runoff_volume_mcm: float = Field(..., description="Total volume in Million Cubic Meters (MCM)")
    peak_discharge_m3s: float = Field(..., description="Estimated peak catchment discharge Qp (m³/s)")
    time_to_peak_hours: float = Field(..., description="Time from storm onset to peak discharge (hours)")
    time_of_concentration_hours: float = Field(..., description="Catchment time of concentration Tc (hours)")


class AccumulationZone(BaseModel):
    """Spatial zone where surface runoff pools or concentrates."""
    zone_id: str = Field(..., description="Unique zone identifier")
    severity: AccumulationSeverity = Field(..., description="LOW, MODERATE, HIGH, EXTREME")
    depth_range_m: str = Field(..., description="Estimated ponding depth range (e.g. '1.5m - 3.0m')")
    area_sqkm: float = Field(..., description="Zone surface area in km²")
    area_percentage: float = Field(..., description="Percentage of catchment area in this zone")
    center_coordinates: List[float] = Field(..., description="[longitude, latitude]")
    geojson_polygon: Optional[Dict[str, Any]] = Field(default=None, description="GeoJSON Polygon boundary")


class WaterFlowParticle(BaseModel):
    """Simulated water movement particle/vector for dynamic map animation."""
    particle_id: str = Field(..., description="Unique particle identifier")
    source_lat: float
    source_lon: float
    dest_lat: float
    dest_lon: float
    velocity_mps: float = Field(default=1.2, description="Estimated flow velocity in m/s")
    stream_order: int = Field(default=1, description="Associated stream reach order")
    time_offset_fraction: float = Field(default=0.0, description="Animation loop phase (0.0 to 1.0)")


class SimulationResult(BaseModel):
    """Comprehensive hydrological simulation result returned by the Digital Twin Engine."""
    simulation_id: str = Field(..., description="Unique simulation execution run ID")
    status: str = Field(default="COMPLETED", description="Status: READY, PROCESSING, RUNNING, COMPLETED, FAILED")
    watershed_id: str = Field(..., description="Target watershed identifier")
    station_name: str = Field(..., description="Target station or catchment name")
    river_name: str = Field(..., description="Monitored river name")
    basin_name: str = Field(..., description="River basin name")
    rainfall_mm: float = Field(..., description="Total rainfall input in mm")
    duration_hours: float = Field(..., description="Rainfall duration in hours")
    rainfall_intensity_mmhr: float = Field(..., description="Average rainfall intensity in mm/hr")
    antecedent_moisture: str = Field(..., description="Moisture condition applied")
    runoff: RunoffSummary
    accumulation_zones: List[AccumulationZone]
    high_accumulation_area_sqkm: float = Field(..., description="Total area under HIGH or EXTREME accumulation (km²)")
    peak_accumulation_depth_m: float = Field(..., description="Max simulated depression ponding depth in meters")
    flow_particles: List[WaterFlowParticle] = Field(default_factory=list)
    geojson_layers: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-packaged GeoJSON layers {watershed, rivers, accumulation, flow_paths}"
    )
    telemetry_badge: str = Field(default="SIMULATED ESTIMATE", description="Disambiguation watermark badge")
    timestamp_utc: str = Field(..., description="ISO 8601 timestamp of simulation run")
    execution_time_ms: float = Field(default=0.0, description="Engine processing duration in milliseconds")
