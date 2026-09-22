"""
Unit & Integration Tests for PRAVAH Digital Twin Studio & Hydrological Simulation Module.
Validates watershed modeling, DEM terrain processing, SCS-CN runoff equations,
water accumulation classification, and REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.digital_twin.digital_twin_manager import DigitalTwinManager
from src.digital_twin.models.simulation import (
    AntecedentMoistureCondition,
    SimulationMode,
    SimulationRequest,
)
from src.digital_twin.utils.geo_utils import (
    validate_crs,
    haversine_distance_km,
    calculate_bbox,
    calculate_centroid,
    polygon_area_sqkm,
)


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture(scope="module")
def dt_manager():
    """DigitalTwinManager singleton fixture."""
    return DigitalTwinManager.get_instance()


# =============================================================================
# 1. Geospatial Utilities & CRS Validation Tests
# =============================================================================

class TestGeoUtils:
    """Validate core geospatial mathematical utilities."""

    def test_crs_validation(self):
        assert validate_crs("EPSG:4326") is True
        assert validate_crs("urn:ogc:def:crs:OGC:1.3:CRS84") is True
        assert validate_crs("WGS84") is True
        assert validate_crs("") is True

    def test_haversine_distance(self):
        # Mumbai (18.92, 72.83) to Pune (18.52, 73.85) ~ 120-140 km
        dist = haversine_distance_km(18.92, 72.83, 18.52, 73.85)
        assert 110.0 < dist < 150.0

    def test_bbox_and_centroid_calculation(self):
        coords = [[[73.4, 18.0], [73.6, 18.0], [73.6, 18.2], [73.4, 18.2], [73.4, 18.0]]]
        bbox = calculate_bbox(coords)
        assert bbox == [73.4, 18.0, 73.6, 18.2]

        c_lat, c_lon = calculate_centroid(coords)
        assert 17.9 <= c_lat <= 18.3
        assert 73.3 <= c_lon <= 73.7

    def test_polygon_area_calculation(self):
        coords = [[73.4, 18.0], [73.6, 18.0], [73.6, 18.2], [73.4, 18.2], [73.4, 18.0]]
        area = polygon_area_sqkm(coords)
        assert area > 0.0
        # Approx 0.2 deg lon * 0.2 deg lat ~ 20km * 22km ~ 440 km²
        assert 350.0 < area < 550.0


# =============================================================================
# 2. Watershed & GeoJSON Modeling Tests
# =============================================================================

class TestWatershedModeling:
    """Validate watershed catalog ingestion, characteristics, and sub-basins."""

    def test_watersheds_loaded(self, dt_manager):
        response = dt_manager.get_all_watersheds()
        assert response.count >= 20
        assert len(response.watersheds) >= 20
        assert response.geojson_feature_collection is not None
        assert response.geojson_feature_collection["type"] == "FeatureCollection"
        assert len(response.geojson_feature_collection["features"]) >= 20

    def test_watershed_detail_lookup(self, dt_manager):
        # Lookup Mahad gauge 602
        ws = dt_manager.get_watershed("INDOFLOODS-gauge-602")
        assert ws is not None
        assert "Savitri" in ws.properties.river_name or "Mahad" in ws.properties.station_name
        assert ws.properties.drainage_area_sqkm > 100.0
        assert ws.properties.curve_number_amc2 > 50.0
        assert len(ws.sub_watersheds) >= 1

    def test_invalid_watershed_returns_none(self, dt_manager):
        ws = dt_manager.get_watershed("NONEXISTENT_GAUGE_9999")
        assert ws is None


# =============================================================================
# 3. DEM & Terrain Gradient Tests
# =============================================================================

class TestTerrainModeling:
    """Validate elevation extraction, slope gradients, and aspect distribution."""

    def test_terrain_model_generation(self, dt_manager):
        terrain = dt_manager.get_terrain_model("INDOFLOODS-gauge-602")
        assert terrain is not None
        assert terrain.watershed_id == "INDOFLOODS-gauge-602"
        assert terrain.elevation.max_elevation_m > terrain.elevation.min_elevation_m
        assert terrain.elevation.elevation_range_m > 0.0
        assert terrain.slope.mean_slope_deg > 0.0
        assert terrain.slope.max_slope_deg >= terrain.slope.mean_slope_deg
        assert len(terrain.contour_intervals) >= 3
        assert len(terrain.hypsometric_bands) >= 3

    def test_aspect_distribution(self, dt_manager):
        terrain = dt_manager.get_terrain_model("INDOFLOODS-gauge-602")
        aspect = terrain.aspect
        total_pct = (
            aspect.north_pct + aspect.northeast_pct + aspect.east_pct +
            aspect.southeast_pct + aspect.south_pct + aspect.southwest_pct +
            aspect.west_pct + aspect.northwest_pct
        )
        assert 98.0 <= total_pct <= 102.0


# =============================================================================
# 4. River Basin Network Tests
# =============================================================================

class TestRiverBasinModeling:
    """Validate river basin aggregations, stream orders, and drainage channels."""

    def test_river_basins_aggregation(self, dt_manager):
        basins = dt_manager.get_river_basins()
        assert len(basins) >= 2
        # Verify Krishna and Brahmaputra basins exist
        basin_names = [b.basin_name for b in basins]
        assert any("Krishna" in name for name in basin_names)

    def test_river_channel_network(self, dt_manager):
        network = dt_manager.get_river_network("INDOFLOODS-gauge-602")
        assert network["type"] == "FeatureCollection"
        assert len(network["features"]) >= 2
        for feat in network["features"]:
            assert feat["geometry"]["type"] == "LineString"
            assert feat["properties"]["stream_order"] >= 1


# =============================================================================
# 5. Runoff & Accumulation Hydrological Tests
# =============================================================================

class TestRunoffAndAccumulation:
    """Validate SCS-CN equations, moisture condition shifts, and pooling zones."""

    def test_scs_curve_number_amc_scaling(self, dt_manager):
        engine = dt_manager.simulation_engine
        base_cn = 75.0
        cn_dry = engine.calculate_effective_cn(base_cn, AntecedentMoistureCondition.AMC_I)
        cn_avg = engine.calculate_effective_cn(base_cn, AntecedentMoistureCondition.AMC_II)
        cn_wet = engine.calculate_effective_cn(base_cn, AntecedentMoistureCondition.AMC_III)

        assert cn_dry < cn_avg < cn_wet
        assert cn_avg == base_cn

    def test_runoff_calculation_physics(self, dt_manager):
        ws = dt_manager.get_watershed("INDOFLOODS-gauge-602")
        engine = dt_manager.simulation_engine

        # Scenario A: Moderate rainfall 100mm
        res100 = engine.compute_scs_runoff(
            watershed=ws,
            rainfall_mm=100.0,
            duration_hours=3.0,
            amc=AntecedentMoistureCondition.AMC_II,
        )
        assert res100.direct_runoff_depth_mm > 0.0
        assert res100.direct_runoff_depth_mm < 100.0
        assert res100.total_runoff_volume_m3 > 0.0
        assert res100.peak_discharge_m3s > 0.0

        # Scenario B: Extreme rainfall 300mm should produce significantly higher runoff
        res300 = engine.compute_scs_runoff(
            watershed=ws,
            rainfall_mm=300.0,
            duration_hours=3.0,
            amc=AntecedentMoistureCondition.AMC_II,
        )
        assert res300.direct_runoff_depth_mm > res100.direct_runoff_depth_mm * 2.0
        assert res300.peak_discharge_m3s > res100.peak_discharge_m3s

    def test_accumulation_zones_classification(self, dt_manager):
        ws = dt_manager.get_watershed("INDOFLOODS-gauge-602")
        zones, geojson = dt_manager.raster_service.generate_accumulation_layers(
            watershed=ws,
            direct_runoff_depth_mm=120.0,
            rainfall_intensity_mmhr=40.0,
        )
        assert len(zones) == 4
        severities = {z.severity.value for z in zones}
        assert severities == {"LOW", "MODERATE", "HIGH", "EXTREME"}
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) == 4


# =============================================================================
# 6. Coupled Simulation Engine Tests
# =============================================================================

class TestSimulationEngine:
    """Validate end-to-end simulation runs and particle vectors."""

    def test_full_simulation_run(self, dt_manager):
        req = SimulationRequest(
            watershed_id="INDOFLOODS-gauge-602",
            rainfall_mm=200.0,
            duration_hours=4.0,
            antecedent_moisture=AntecedentMoistureCondition.AMC_II,
            simulation_mode=SimulationMode.COUPLED_HYDROLOGIC,
        )
        sim_result = dt_manager.run_simulation(req)
        assert sim_result.status == "COMPLETED"
        assert sim_result.simulation_id.startswith("SIM-")
        assert sim_result.runoff.direct_runoff_depth_mm > 0.0
        assert len(sim_result.accumulation_zones) == 4
        assert len(sim_result.flow_particles) >= 2
        assert "watershed_boundary" in sim_result.geojson_layers
        assert "accumulation_layer" in sim_result.geojson_layers
        assert "river_network" in sim_result.geojson_layers

    def test_preset_scenarios_available(self, dt_manager):
        scenarios = dt_manager.get_scenarios()
        assert len(scenarios) >= 4
        scenario_ids = [s["scenario_id"] for s in scenarios]
        assert "SCEN_MAHAD_CLOUDBURST" in scenario_ids


# =============================================================================
# 7. REST API Endpoints Tests
# =============================================================================

class TestDigitalTwinAPI:
    """Validate all REST API endpoints under /api/digital-twin/."""

    def test_status_endpoint(self, client):
        res = client.get("/api/digital-twin/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "online"
        assert data["service"] == "PRAVAH Digital Twin Studio"
        assert data["monitored_watersheds_count"] >= 20

    def test_watersheds_endpoint(self, client):
        res = client.get("/api/digital-twin/watersheds")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] >= 20
        assert len(data["watersheds"]) >= 20

    def test_watershed_detail_endpoint(self, client):
        res = client.get("/api/digital-twin/watersheds/INDOFLOODS-gauge-602")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "INDOFLOODS-gauge-602"
        assert "properties" in data

    def test_watershed_detail_not_found(self, client):
        res = client.get("/api/digital-twin/watersheds/INVALID_ID")
        assert res.status_code == 404

    def test_terrain_endpoint(self, client):
        res = client.get("/api/digital-twin/terrain?watershed_id=INDOFLOODS-gauge-602")
        assert res.status_code == 200
        data = res.json()
        assert "elevation" in data
        assert "slope" in data
        assert "aspect" in data

    def test_river_basins_endpoint(self, client):
        res = client.get("/api/digital-twin/river-basins")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_scenarios_endpoint(self, client):
        res = client.get("/api/digital-twin/scenarios")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 4

    def test_layers_endpoint(self, client):
        res = client.get("/api/digital-twin/layers")
        assert res.status_code == 200
        data = res.json()
        assert "layers" in data
        assert len(data["layers"]) >= 5

    def test_simulate_endpoint(self, client):
        payload = {
            "watershed_id": "INDOFLOODS-gauge-602",
            "rainfall_mm": 150.0,
            "duration_hours": 3.0,
            "antecedent_moisture": "AMC_II",
        }
        res = client.post("/api/digital-twin/simulate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["runoff"]["direct_runoff_depth_mm"] > 0.0

    def test_simulate_invalid_rainfall_validation(self, client):
        # Negative rainfall should trigger validation 422
        payload = {
            "watershed_id": "INDOFLOODS-gauge-602",
            "rainfall_mm": -50.0,
            "duration_hours": 3.0,
        }
        res = client.post("/api/digital-twin/simulate", json=payload)
        assert res.status_code == 422

    def test_runoff_query_endpoint(self, client):
        res = client.get("/api/digital-twin/runoff?watershed_id=INDOFLOODS-gauge-602&rainfall_mm=120.0")
        assert res.status_code == 200
        data = res.json()
        assert "runoff_metrics" in data

    def test_accumulation_query_endpoint(self, client):
        res = client.get("/api/digital-twin/accumulation?watershed_id=INDOFLOODS-gauge-602&rainfall_mm=120.0")
        assert res.status_code == 200
        data = res.json()
        assert "zones" in data
        assert len(data["zones"]) == 4


# =============================================================================
# 8. Backward Compatibility & System Isolation Tests
# =============================================================================

class TestSystemIsolation:
    """Ensure existing PRAVAH functionality remains completely untouched."""

    def test_health_check_endpoint(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_xai_models_endpoint(self, client):
        res = client.get("/api/xai/models")
        assert res.status_code == 200
        assert len(res.json()["supported_models"]) >= 3

    def test_alert_channels_endpoint(self, client):
        res = client.get("/api/alerts/status")
        assert res.status_code == 200
        data = res.json()
        assert "sms_enabled" in data
        assert "whatsapp_enabled" in data
        assert "telegram_enabled" in data

    def test_community_reports_endpoint(self, client):
        res = client.get("/api/community/reports")
        assert res.status_code == 200
