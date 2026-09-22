"""
PRAVAH Digital Twin — Central Orchestrator (DigitalTwinManager).
Coordinates DEM processing, GeoJSON watershed datasets, river-basin networks,
and hydrological simulation execution.
"""

import logging
from typing import Any, Dict, List, Optional

from src.digital_twin.models.watershed import (
    Watershed,
    WatershedProperties,
    WatershedListResponse,
)
from src.digital_twin.models.terrain import TerrainModelOutput
from src.digital_twin.models.river_basin import RiverBasinSummary, RiverBasinNetwork
from src.digital_twin.models.simulation import (
    SimulationRequest,
    SimulationResult,
)
from src.digital_twin.services.geojson_service import GeoJsonService
from src.digital_twin.services.dem_service import DEMService
from src.digital_twin.services.raster_service import RasterService
from src.digital_twin.services.simulation_service import SimulationService
from src.digital_twin.simulation_engine import SimulationEngine

logger = logging.getLogger("pravah.digital_twin.manager")


class DigitalTwinManager:
    """
    Central coordinator orchestrating all Digital Twin components, data pipelines,
    and simulation capabilities.
    """

    _instance: Optional["DigitalTwinManager"] = None

    def __init__(
        self,
        geojson_service: Optional[GeoJsonService] = None,
        dem_service: Optional[DEMService] = None,
        raster_service: Optional[RasterService] = None,
        simulation_service: Optional[SimulationService] = None,
        simulation_engine: Optional[SimulationEngine] = None,
    ):
        self.geojson_service = geojson_service or GeoJsonService()
        self.dem_service = dem_service or DEMService()
        self.raster_service = raster_service or RasterService()
        self.simulation_service = simulation_service or SimulationService()
        self.simulation_engine = simulation_engine or SimulationEngine(raster_service=self.raster_service)
        logger.info("DigitalTwinManager initialized successfully.")

    @classmethod
    def get_instance(cls) -> "DigitalTwinManager":
        """Singleton accessor for DigitalTwinManager."""
        if cls._instance is None:
            cls._instance = DigitalTwinManager()
        return cls._instance

    # -------------------------------------------------------------------------
    # Watershed Query Methods
    # -------------------------------------------------------------------------

    def get_all_watersheds(self) -> WatershedListResponse:
        """List all available watersheds with metadata and GeoJSON boundaries."""
        properties_list = self.geojson_service.get_all_watersheds()
        fc = self.geojson_service.get_geojson_feature_collection()
        return WatershedListResponse(
            count=len(properties_list),
            watersheds=properties_list,
            geojson_feature_collection=fc,
        )

    def get_watershed(self, watershed_id: str) -> Optional[Watershed]:
        """Retrieve detailed watershed entity by ID."""
        return self.geojson_service.get_watershed_by_id(watershed_id)

    # -------------------------------------------------------------------------
    # Terrain & DEM Modeling Methods
    # -------------------------------------------------------------------------

    def get_terrain_model(self, watershed_id: str) -> Optional[TerrainModelOutput]:
        """Derive or retrieve DEM terrain gradients, slope, and aspect for a watershed."""
        ws = self.geojson_service.get_watershed_by_id(watershed_id)
        if not ws:
            return None
        return self.dem_service.generate_terrain_model(ws)

    # -------------------------------------------------------------------------
    # River Basin Methods
    # -------------------------------------------------------------------------

    def get_river_basins(self) -> List[RiverBasinSummary]:
        """List aggregated river basins."""
        return self.geojson_service.get_river_basins_summary()

    def get_river_network(self, watershed_id: str) -> Dict[str, Any]:
        """Retrieve river reaches and drainage paths for a given watershed."""
        ws = self.geojson_service.get_watershed_by_id(watershed_id)
        if not ws:
            return {"type": "FeatureCollection", "features": []}
        features, _ = self.raster_service.generate_flow_network(ws)
        return {
            "type": "FeatureCollection",
            "features": features,
        }

    # -------------------------------------------------------------------------
    # Simulation Execution Methods
    # -------------------------------------------------------------------------

    def run_simulation(self, request: SimulationRequest) -> SimulationResult:
        """
        Validate inputs, execute coupled SCS-CN runoff and accumulation simulation,
        and cache results.
        """
        ws = self.geojson_service.get_watershed_by_id(request.watershed_id)
        if not ws:
            # Fallback to first available watershed if requested ID not found
            all_ws = self.geojson_service.get_all_watersheds()
            if all_ws:
                fallback_id = all_ws[0].watershed_id
                ws = self.geojson_service.get_watershed_by_id(fallback_id)
                logger.warning(
                    "Requested watershed '%s' not found; defaulting to fallback '%s'",
                    request.watershed_id,
                    fallback_id,
                )

        if not ws:
            raise ValueError(f"No valid watershed found for ID: {request.watershed_id}")

        result = self.simulation_engine.run_simulation(ws, request)
        self.simulation_service.record_simulation(result)
        return result

    def get_simulation_result(self, simulation_id: str) -> Optional[SimulationResult]:
        """Retrieve historical simulation output."""
        return self.simulation_service.get_simulation_by_id(simulation_id)

    def get_scenarios(self) -> List[Dict[str, Any]]:
        """Retrieve benchmark flood scenarios."""
        return self.simulation_service.get_preset_scenarios()

    def get_layer_manifest(self) -> Dict[str, Any]:
        """Return available visualization layer metadata and default toggles."""
        return {
            "layers": [
                {
                    "layer_id": "watershed_boundaries",
                    "name": "Watershed Boundaries",
                    "type": "vector",
                    "default_visible": True,
                    "description": "Geospatial catchment boundaries and sub-basins.",
                },
                {
                    "layer_id": "terrain_elevation",
                    "name": "Terrain Elevation & Slope",
                    "type": "hypsometric",
                    "default_visible": True,
                    "description": "Topographic elevation contours and slope gradient bands.",
                },
                {
                    "layer_id": "river_network",
                    "name": "River Basin & Streams",
                    "type": "vector_stream",
                    "default_visible": True,
                    "description": "Strahler stream network classified by tributary order.",
                },
                {
                    "layer_id": "runoff_flow_paths",
                    "name": "Runoff Flow Paths",
                    "type": "particle_vector",
                    "default_visible": True,
                    "description": "Simulated dynamic downhill water movement vectors.",
                },
                {
                    "layer_id": "water_accumulation",
                    "name": "Water Accumulation Heatmap",
                    "type": "accumulation_zones",
                    "default_visible": True,
                    "description": "Topological pooling zones classified from LOW to EXTREME.",
                },
                {
                    "layer_id": "flood_risk_gauges",
                    "name": "Critical Gauge Indicators",
                    "type": "markers",
                    "default_visible": True,
                    "description": "CWC / INDOFLOODS monitoring stations with warning stages.",
                },
            ]
        }
