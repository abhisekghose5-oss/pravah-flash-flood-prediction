"""
PRAVAH Flood Propagation — Scenario Models.
Defines schemas for simulation scenarios (Rainfall, Dam Release, River Overflow)
and simulation periods (1h, 6h, 12h, 24h, 48h).
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class ScenarioType(str, Enum):
    """Primary flood trigger scenario category."""
    RAINFALL = "rainfall"
    DAM_RELEASE = "dam_release"
    RIVER_OVERFLOW = "river_overflow"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_norm = value.lower().replace("_event", "").replace("-", "_").strip()
            for member in cls:
                if member.value == val_norm or member.name.lower() == val_norm:
                    return member
        return None


class SimulationPeriod(int, Enum):
    """Supported simulation time horizons in hours."""
    PERIOD_1H = 1
    PERIOD_6H = 6
    PERIOD_12H = 12
    PERIOD_24H = 24
    PERIOD_48H = 48


class SpatialDistribution(str, Enum):
    """Precipitation spatial distribution pattern."""
    UNIFORM = "uniform"
    CONVECTIVE_CORE = "convective_core"
    OROGRAPHIC_CREST = "orographic_crest"


class RainfallScenarioParams(BaseModel):
    """Input parameters for a precipitation-driven flood event."""
    rainfall_mm: float = Field(..., ge=1.0, le=1000.0, description="Total cumulative precipitation in mm")
    rainfall_duration_hours: float = Field(default=6.0, ge=0.5, le=48.0, description="Rainfall storm duration in hours")
    spatial_distribution: SpatialDistribution = Field(
        default=SpatialDistribution.CONVECTIVE_CORE,
        description="Rainfall pattern across catchment"
    )
    catchment_id: str = Field(default="INDOFLOODS-gauge-602", description="Target catchment / gauge ID")
    initial_soil_saturation_pct: float = Field(default=65.0, ge=0.0, le=100.0, description="Initial antecedent soil moisture %")

    @model_validator(mode='before')
    @classmethod
    def check_rainfall_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "rainfall_mm" not in d or d["rainfall_mm"] is None:
                duration = float(d.get("rainfall_duration_hours") or d.get("duration_hours") or 6.0)
                if "intensity_mm_per_hr" in d and d["intensity_mm_per_hr"] is not None:
                    d["rainfall_mm"] = min(1000.0, max(1.0, float(d["intensity_mm_per_hr"]) * duration))
                elif "intensity_mm" in d and d["intensity_mm"] is not None:
                    d["rainfall_mm"] = float(d["intensity_mm"])
                elif "rainfall" in d and d["rainfall"] is not None:
                    d["rainfall_mm"] = float(d["rainfall"])
                elif "precipitation_mm" in d and d["precipitation_mm"] is not None:
                    d["rainfall_mm"] = float(d["precipitation_mm"])
            return d
        return data


class DamReleaseScenarioParams(BaseModel):
    """Input parameters for a controlled or emergency reservoir discharge."""
    dam_id: str = Field(..., description="Dam / reservoir identifier (e.g. DAM_KOYNA, DAM_UJANI)")
    dam_name: str = Field(..., description="Name of the dam or reservoir")
    river_basin: str = Field(default="Krishna", description="Downstream river basin")
    release_rate_m3s: float = Field(..., ge=50.0, le=25000.0, description="Discharge outflow rate in m³/s")
    release_duration_hours: float = Field(default=4.0, ge=0.5, le=48.0, description="Duration of sustained discharge in hours")
    downstream_safe_capacity_m3s: float = Field(default=2500.0, description="Bankfull non-flood conveyance capacity in m³/s")
    reservoir_level_pct: float = Field(default=92.0, ge=10.0, le=100.0, description="Pre-release reservoir storage fullness %")
    operational_disclaimer: str = Field(
        default="SIMULATED SCENARIO ONLY — Not an operational dam release instruction.",
        description="Mandatory disclaimer string"
    )


class RiverOverflowScenarioParams(BaseModel):
    """Input parameters for river stage cresting and bank breach simulation."""
    river_id: str = Field(..., description="River or reach identifier (e.g. RIVER_SAVITRI, RIVER_KRISHNA)")
    river_name: str = Field(..., description="River name")
    gauge_id: str = Field(default="INDOFLOODS-gauge-602", description="Monitoring gauge station ID")
    initial_water_level_m: float = Field(default=8.0, ge=0.5, le=50.0, description="Starting river stage in meters")
    overflow_threshold_m: float = Field(default=11.0, ge=1.0, le=50.0, description="River bankfull / danger mark stage in meters")
    simulated_water_level_m: float = Field(..., ge=1.0, le=60.0, description="Peak cresting stage in meters")
    duration_hours: float = Field(default=8.0, ge=0.5, le=48.0, description="Duration of stage elevation above threshold")
    overtopping_duration_hours: Optional[float] = Field(default=None, description="Alias for duration_hours")
    breach_width_m: float = Field(default=45.0, ge=5.0, le=250.0, description="Estimated levee / embankment breach width in meters")

    def model_post_init(self, __context: Any) -> None:
        if self.overtopping_duration_hours is not None and self.duration_hours == 8.0:
            self.duration_hours = self.overtopping_duration_hours


class ScenarioTemplate(BaseModel):
    """Metadata template for a preset scenario available in the simulation library."""
    template_id: str
    scenario_type: ScenarioType
    title: str
    description: str
    region: str
    default_period_hours: SimulationPeriod
    parameters: Dict[str, Any]
