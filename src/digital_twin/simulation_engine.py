"""
PRAVAH Digital Twin — Hydrological Simulation Engine.
Implements SCS Curve Number (SCS-CN) runoff modeling, antecedent moisture condition
adjustments, unit hydrograph peak discharge calculation, topological water accumulation,
and drainage particle trajectory synthesis.
"""

from datetime import datetime, timezone
import logging
import math
import time
import uuid
from typing import Any, Dict, List, Optional

from src.digital_twin.models.watershed import Watershed
from src.digital_twin.models.simulation import (
    AntecedentMoistureCondition,
    SimulationMode,
    SimulationRequest,
    SimulationResult,
    RunoffSummary,
    AccumulationZone,
    WaterFlowParticle,
)
from src.digital_twin.services.raster_service import RasterService

logger = logging.getLogger("pravah.digital_twin.engine")


class SimulationEngine:
    """
    Hydrological simulation engine executing physical rainfall-runoff
    transformations, accumulation zone mapping, and drainage vector generation.
    """

    def __init__(self, raster_service: Optional[RasterService] = None):
        self.raster_service = raster_service or RasterService()

    def calculate_effective_cn(
        self,
        base_cn: float,
        amc: AntecedentMoistureCondition
    ) -> float:
        """
        Adjust standard AMC-II Curve Number according to Antecedent Moisture Condition (AMC).
        - AMC I: Dry soil prior to precipitation event.
        - AMC II: Average / normal seasonal condition.
        - AMC III: Saturated / wet soil from preceding rainfall.
        """
        cn2 = max(30.0, min(98.0, base_cn))
        if amc == AntecedentMoistureCondition.AMC_I:
            # Hawkins et al. dry adjustment
            cn1 = cn2 / (2.281 - 0.01281 * cn2)
            return round(max(25.0, min(95.0, cn1)), 1)
        elif amc == AntecedentMoistureCondition.AMC_III:
            # Hawkins et al. wet adjustment
            cn3 = cn2 / (0.427 + 0.00573 * cn2)
            return round(max(35.0, min(99.0, cn3)), 1)
        return round(cn2, 1)

    def compute_scs_runoff(
        self,
        watershed: Watershed,
        rainfall_mm: float,
        duration_hours: float,
        amc: AntecedentMoistureCondition = AntecedentMoistureCondition.AMC_II,
    ) -> RunoffSummary:
        """
        Compute surface runoff depth, volume, and hydrograph peak discharge using SCS-CN method.
        """
        props = watershed.properties
        area_sqkm = max(1.0, props.drainage_area_sqkm)
        tc_hr = max(1.0, props.time_of_concentration_hr)

        effective_cn = self.calculate_effective_cn(props.curve_number_amc2, amc)

        # Potential maximum soil retention S in mm
        # S = 25400 / CN - 254
        s_mm = (25400.0 / effective_cn) - 254.0

        # Initial abstraction Ia = 0.2 * S
        ia_mm = 0.2 * s_mm

        # Direct runoff depth Q = (P - Ia)^2 / (P - Ia + S) for P > Ia
        p_mm = max(0.0, rainfall_mm)
        if p_mm > ia_mm:
            runoff_depth_mm = ((p_mm - ia_mm) ** 2) / (p_mm - ia_mm + s_mm)
        else:
            runoff_depth_mm = 0.0

        runoff_coeff = runoff_depth_mm / p_mm if p_mm > 0 else 0.0

        # Total runoff volume V = Q (m) * Area (m²)
        runoff_vol_m3 = (runoff_depth_mm / 1000.0) * (area_sqkm * 1_000_000.0)
        runoff_vol_mcm = runoff_vol_m3 / 1_000_000.0

        # Time to peak hydrograph: Tp = 0.5 * D + 0.6 * Tc
        time_to_peak_hr = 0.5 * duration_hours + 0.6 * tc_hr

        # Peak discharge Qp using SCS dimensionless unit hydrograph peak formula:
        # Qp (m³/s) = (0.208 * Area_km² * Q_mm) / Tp_hr
        peak_q_m3s = (0.208 * area_sqkm * runoff_depth_mm) / max(0.5, time_to_peak_hr)

        return RunoffSummary(
            curve_number_applied=effective_cn,
            potential_retention_s_mm=round(s_mm, 2),
            initial_abstraction_ia_mm=round(ia_mm, 2),
            effective_rainfall_p_mm=round(p_mm, 2),
            direct_runoff_depth_mm=round(runoff_depth_mm, 2),
            runoff_coefficient=round(runoff_coeff, 3),
            total_runoff_volume_m3=round(runoff_vol_m3, 2),
            total_runoff_volume_mcm=round(runoff_vol_mcm, 3),
            peak_discharge_m3s=round(peak_q_m3s, 2),
            time_to_peak_hours=round(time_to_peak_hr, 2),
            time_of_concentration_hours=round(tc_hr, 2),
        )

    def run_simulation(
        self,
        watershed: Watershed,
        request: SimulationRequest
    ) -> SimulationResult:
        """
        Execute comprehensive coupled hydrological simulation.
        Produces runoff summary, water accumulation footprints, animated particle vectors,
        and Leaflet GeoJSON layer packages.
        """
        start_time = time.time()
        props = watershed.properties
        sim_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"

        # 1. Runoff Modeling
        runoff = self.compute_scs_runoff(
            watershed=watershed,
            rainfall_mm=request.rainfall_mm,
            duration_hours=request.duration_hours,
            amc=request.antecedent_moisture,
        )

        intensity_mmhr = request.rainfall_mm / max(0.1, request.duration_hours)

        # 2. Water Accumulation Modeling
        acc_zones, acc_geojson = self.raster_service.generate_accumulation_layers(
            watershed=watershed,
            direct_runoff_depth_mm=runoff.direct_runoff_depth_mm,
            rainfall_intensity_mmhr=intensity_mmhr,
        )

        # High + Extreme accumulation total area
        high_acc_area = sum(
            z.area_sqkm for z in acc_zones if z.severity in ["HIGH", "EXTREME"]
        )

        # 3. Flow paths and animated particles
        river_segments, particles = self.raster_service.generate_flow_network(watershed)

        # Pre-package Leaflet GeoJSON layers
        layers_bundle = {
            "watershed_boundary": {
                "type": "Feature",
                "id": watershed.id,
                "properties": props.model_dump(),
                "geometry": watershed.geometry,
            },
            "accumulation_layer": acc_geojson,
            "river_network": {
                "type": "FeatureCollection",
                "features": river_segments,
            }
        }

        # Peak accumulation depth estimate
        peak_depth_m = 1.0 + (runoff.direct_runoff_depth_mm / 30.0) * 0.75

        execution_ms = (time.time() - start_time) * 1000.0

        return SimulationResult(
            simulation_id=sim_id,
            status="COMPLETED",
            watershed_id=props.watershed_id,
            station_name=props.station_name,
            river_name=props.river_name,
            basin_name=props.basin_name,
            rainfall_mm=request.rainfall_mm,
            duration_hours=request.duration_hours,
            rainfall_intensity_mmhr=round(intensity_mmhr, 2),
            antecedent_moisture=request.antecedent_moisture.value,
            runoff=runoff,
            accumulation_zones=acc_zones,
            high_accumulation_area_sqkm=round(high_acc_area, 2),
            peak_accumulation_depth_m=round(peak_depth_m, 2),
            flow_particles=particles,
            geojson_layers=layers_bundle,
            telemetry_badge="SIMULATED ESTIMATE",
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=round(execution_ms, 2),
        )
