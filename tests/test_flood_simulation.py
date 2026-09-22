"""
Unit & Integration Tests for PRAVAH Flood Propagation & Inundation Simulation Engine.
Validates:
- Geospatial utilities & dynamic wave polygon generation
- Multi-scenario engines: Rainfall, Dam Release, River Overflow
- 5-tier depth classification & multi-step propagation
- Demographic exposure from census data & OSM infrastructure impact
- Central SimulationManager & API endpoints under /api/simulation/
- System isolation & non-regression of existing prediction pipelines
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.simulation.models.scenario import (
    ScenarioType,
    SimulationPeriod,
    SpatialDistribution,
    RainfallScenarioParams,
    DamReleaseScenarioParams,
    RiverOverflowScenarioParams,
)
from src.simulation.models.simulation import SimulationRunRequest
from src.simulation.utils.geo_utils import (
    haversine_km,
    generate_propagation_polygon,
    is_point_within_radius,
)
from src.simulation.utils.simulation_utils import (
    get_discrete_time_steps,
    propagation_fraction,
)
from src.simulation.scenarios.rainfall import RainfallScenario
from src.simulation.scenarios.dam_release import DamReleaseScenario
from src.simulation.scenarios.river_overflow import RiverOverflowScenario
from src.simulation.inundation_engine import InundationEngine
from src.simulation.impact_engine import ImpactEngine
from src.simulation.propagation_engine import FloodPropagationEngine
from src.simulation.simulation_manager import get_simulation_manager


@pytest.fixture(scope="module")
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


@pytest.fixture(scope="module")
def sim_manager():
    """SimulationManager singleton fixture."""
    return get_simulation_manager()


# =============================================================================
# 1. Geospatial & Computational Utilities
# =============================================================================

class TestGeoAndSimulationUtils:
    """Validate mathematical and geometric helper functions."""

    def test_haversine_distance(self):
        # Mahad (18.0922, 73.4603) to Karad (17.2889, 74.1814) ~ 110-130 km
        dist = haversine_km(18.0922, 73.4603, 17.2889, 74.1814)
        assert 100.0 < dist < 140.0

    def test_haversine_zero_distance(self):
        assert haversine_km(18.52, 73.85, 18.52, 73.85) == 0.0

    def test_generate_propagation_polygon(self):
        poly = generate_propagation_polygon(
            center_lat=18.0,
            center_lon=73.5,
            radius_km=5.0,
            num_points=24,
        )
        assert isinstance(poly, dict)
        assert poly["type"] == "Polygon"
        coords = poly["coordinates"][0]
        assert len(coords) == 25  # Closed ring (24 points + 1 start)
        assert coords[0] == coords[-1]

    def test_point_within_radius(self):
        assert is_point_within_radius(18.01, 73.51, 18.0, 73.5, radius_km=5.0) is True
        assert is_point_within_radius(19.0, 74.5, 18.0, 73.5, radius_km=5.0) is False

    def test_discrete_time_steps_generation(self):
        assert get_discrete_time_steps(1) == [0.0, 0.25, 0.5, 0.75, 1.0]
        assert get_discrete_time_steps(6) == [0.0, 1.0, 2.0, 4.0, 6.0]
        assert get_discrete_time_steps(24) == [0.0, 1.0, 3.0, 6.0, 12.0, 18.0, 24.0]

    def test_propagation_fraction_monotonicity(self):
        steps = [0.0, 2.0, 6.0, 12.0, 24.0]
        fractions = [propagation_fraction(t, 24.0) for t in steps]
        assert fractions[0] == 0.0
        assert fractions[-1] == 1.0
        for i in range(len(fractions) - 1):
            assert fractions[i] <= fractions[i + 1]


# =============================================================================
# 2. Multi-Scenario Mathematical Physics
# =============================================================================

class TestScenarioPhysics:
    """Validate scenario propagation logic for Rainfall, Dam, and River."""

    def test_rainfall_scenario_propagation(self):
        params = RainfallScenarioParams(
            rainfall_mm=250.0,
            rainfall_duration_hours=6.0,
            spatial_distribution=SpatialDistribution.CONVECTIVE_CORE,
            catchment_id="INDOFLOODS-gauge-602",
            initial_soil_saturation_pct=85.0,
        )
        scenario = RainfallScenario(params)
        step_early = scenario.compute_propagation(elapsed_hours=1.0, total_period_hours=24, centroid=(18.0, 73.5))
        step_peak = scenario.compute_propagation(elapsed_hours=6.0, total_period_hours=24, centroid=(18.0, 73.5))

        assert step_peak["flooded_area_km2"] >= step_early["flooded_area_km2"]
        assert step_peak["peak_depth_m"] >= step_early["peak_depth_m"]
        assert step_peak["peak_depth_m"] > 0.0
        assert step_peak["flooded_area_km2"] > 0.0

    def test_dam_release_scenario_propagation(self):
        params = DamReleaseScenarioParams(
            dam_id="DAM_KOYNA",
            dam_name="Koyna Dam",
            river_basin="Krishna",
            release_rate_m3s=5000.0,
            release_duration_hours=4.0,
            downstream_safe_capacity_m3s=2500.0,
            reservoir_level_pct=96.0,
        )
        scenario = DamReleaseScenario(params)
        step_1h = scenario.compute_propagation(elapsed_hours=1.0, total_period_hours=24, dam_coords=(17.4, 73.75))
        step_12h = scenario.compute_propagation(elapsed_hours=12.0, total_period_hours=24, dam_coords=(17.4, 73.75))

        # Downstream movement of centroid
        assert step_12h["center_lat"] < step_1h["center_lat"] or step_12h["center_lon"] > step_1h["center_lon"]
        assert step_12h["flooded_area_km2"] > 0.0
        assert step_12h["peak_depth_m"] > 0.0

    def test_river_overflow_scenario_propagation(self):
        params = RiverOverflowScenarioParams(
            river_id="RIVER_SAVITRI",
            river_name="Savitri River",
            gauge_id="INDOFLOODS-gauge-602",
            simulated_water_level_m=13.5,
            overflow_threshold_m=11.0,
            breach_width_m=80.0,
            overtopping_duration_hours=8.0,
        )
        scenario = RiverOverflowScenario(params)
        step = scenario.compute_propagation(elapsed_hours=4.0, total_period_hours=12, river_coords=(18.09, 73.46))

        assert step["peak_depth_m"] > 0.5
        assert step["flooded_area_km2"] > 0.1
        assert step["flood_radius_km"] > 0.2


# =============================================================================
# 3. Inundation & Impact Calculation Engines
# =============================================================================

class TestInundationAndImpactEngines:
    """Validate 5-tier depth mapping, census population exposure, and infrastructure risks."""

    def test_inundation_engine_tiers(self):
        engine = InundationEngine()
        step_inun = engine.generate_timestep_inundation(
            time_hours=6.0,
            time_label="T+6h",
            center_lat=18.09,
            center_lon=73.46,
            flood_radius_km=3.5,
            flooded_area_km2=12.5,
            peak_depth_m=2.8,
        )
        assert step_inun.total_extent_km2 == 12.5
        assert step_inun.depth_stats.max_depth_m == 2.8
        assert "LOW" in step_inun.severity_breakdown_km2
        assert "MODERATE" in step_inun.severity_breakdown_km2

        # Validate GeoJSON FeatureCollection
        fc = step_inun.geojson_feature_collection
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) >= 3

    def test_impact_engine_population_and_infrastructure(self):
        engine = ImpactEngine()
        impact = engine.evaluate_step_impact(
            time_hours=6.0,
            time_label="T+6h",
            catchment_id="INDOFLOODS-gauge-602",
            center_lat=18.0922,
            center_lon=73.4603,
            flooded_area_km2=15.0,
            flood_radius_km=4.0,
            peak_depth_m=2.2,
        )

        pop_exp = impact.population
        infra_summary = impact.infrastructure

        assert pop_exp.estimated_population_exposed > 0
        assert pop_exp.high_risk_population >= 0
        assert pop_exp.evacuation_urgency in ["MONITORING", "ADVISORY", "URGENT", "MANDATORY"]
        assert infra_summary.submerged_road_length_km >= 0.0
        assert infra_summary.threatened_critical_facilities >= 0


# =============================================================================
# 4. Full FloodPropagationEngine Execution
# =============================================================================

class TestFloodPropagationEngine:
    """Execute end-to-end multi-step simulations."""

    def test_execute_rainfall_simulation(self):
        engine = FloodPropagationEngine()
        req = SimulationRunRequest(
            scenario_type=ScenarioType.RAINFALL,
            simulation_period_hours=SimulationPeriod.PERIOD_12H,
            rainfall_params=RainfallScenarioParams(
                rainfall_mm=180.0,
                rainfall_duration_hours=4.0,
                spatial_distribution=SpatialDistribution.CONVECTIVE_CORE,
                catchment_id="INDOFLOODS-gauge-602",
                initial_soil_saturation_pct=75.0,
            ),
        )
        res = engine.execute_simulation(req)

        assert res.status == "COMPLETED"
        assert res.simulation_id.startswith("SIM-")
        assert res.maximum_flood_extent_km2 > 0.0
        assert res.peak_depth_m > 0.0
        assert res.total_population_impacted > 0
        assert len(res.time_steps) > 0
        assert len(res.growth_timeline) == len(res.time_steps)
        assert len(res.impact_timeline) == len(res.time_steps)
        assert "SIMULATED ESTIMATE" in res.provenance_disclaimer

    def test_execute_dam_release_simulation(self):
        engine = FloodPropagationEngine()
        req = SimulationRunRequest(
            scenario_type=ScenarioType.DAM_RELEASE,
            simulation_period_hours=SimulationPeriod.PERIOD_6H,
            dam_release_params=DamReleaseScenarioParams(
                dam_id="DAM_KOYNA",
                dam_name="Koyna Dam",
                river_basin="Krishna",
                release_rate_m3s=4000.0,
                release_duration_hours=3.0,
                downstream_safe_capacity_m3s=2500.0,
                reservoir_level_pct=92.0,
            ),
        )
        res = engine.execute_simulation(req)

        assert res.status == "COMPLETED"
        assert res.scenario_type == ScenarioType.DAM_RELEASE
        assert res.maximum_flood_extent_km2 > 0.0

    def test_execute_river_overflow_simulation(self):
        engine = FloodPropagationEngine()
        req = SimulationRunRequest(
            scenario_type=ScenarioType.RIVER_OVERFLOW,
            simulation_period_hours=SimulationPeriod.PERIOD_1H,
            river_overflow_params=RiverOverflowScenarioParams(
                river_id="RIVER_SAVITRI",
                river_name="Savitri River",
                gauge_id="INDOFLOODS-gauge-602",
                simulated_water_level_m=12.5,
                overflow_threshold_m=11.0,
                breach_width_m=50.0,
                overtopping_duration_hours=2.0,
            ),
        )
        res = engine.execute_simulation(req)

        assert res.status == "COMPLETED"
        assert res.scenario_type == ScenarioType.RIVER_OVERFLOW
        assert len(res.time_steps) == 5  # [0, 0.25, 0.5, 0.75, 1.0]


# =============================================================================
# 5. SimulationManager Cache & Multi-Tier Queries
# =============================================================================

class TestSimulationManager:
    """Test central manager caching, lookup, cancellation, and presets."""

    def test_run_and_cache(self, sim_manager):
        req = SimulationRunRequest(
            scenario_type=ScenarioType.RAINFALL,
            simulation_period_hours=SimulationPeriod.PERIOD_6H,
            rainfall_params=RainfallScenarioParams(
                rainfall_mm=120.0,
                rainfall_duration_hours=3.0,
                spatial_distribution=SpatialDistribution.UNIFORM,
                catchment_id="INDOFLOODS-gauge-684",
                initial_soil_saturation_pct=70.0,
            ),
        )
        res = sim_manager.run_simulation(req)
        sim_id = res.simulation_id

        # Retrieve cached simulation
        cached = sim_manager.get_simulation(sim_id)
        assert cached is not None
        assert cached.simulation_id == sim_id

        # Query inundation
        inundation = sim_manager.get_simulation_inundation(sim_id)
        assert inundation is not None
        assert "time_steps" in inundation

        # Query specific step inundation
        step_inundation = sim_manager.get_simulation_inundation(sim_id, time_step_hour=4.0)
        assert step_inundation is not None
        assert "geojson" in step_inundation

        # Query population impact
        pop = sim_manager.get_population_impact(sim_id)
        assert pop is not None
        assert "peak_population_exposed" in pop

        # Query infrastructure impact
        infra = sim_manager.get_infrastructure_impact(sim_id)
        assert infra is not None
        assert "final_summary" in infra

        # Query lightweight timeline
        tl = sim_manager.get_timeline(sim_id)
        assert tl is not None
        assert len(tl.growth_points) > 0
        assert len(tl.population_points) > 0

    def test_list_history_and_presets(self, sim_manager):
        history = sim_manager.list_history(limit=10)
        assert isinstance(history, list)
        assert len(history) >= 1

        presets = sim_manager.get_scenario_templates()
        assert len(presets) >= 3
        types = [p.scenario_type for p in presets]
        assert ScenarioType.RAINFALL in types
        assert ScenarioType.DAM_RELEASE in types
        assert ScenarioType.RIVER_OVERFLOW in types


# =============================================================================
# 6. REST API Endpoints (/api/simulation/...)
# =============================================================================

class TestSimulationEndpoints:
    """Validate all HTTP routes mounted under /api/simulation."""

    def test_get_status(self, client):
        resp = client.get("/api/simulation/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "OPERATIONAL"
        assert "monitored_rivers" in data
        assert "monitored_dams" in data
        assert "Koyna Dam" in data["monitored_dams"]

    def test_get_scenarios(self, client):
        resp = client.get("/api/simulation/scenarios")
        assert resp.status_code == 200
        scenarios = resp.json()
        assert len(scenarios) >= 3
        assert any(s["template_id"] == "SCEN_RAINFALL_MAHAD" for s in scenarios)

    def test_post_simulation_run(self, client):
        payload = {
            "scenario_type": "rainfall",
            "simulation_period_hours": 6,
            "rainfall_params": {
                "rainfall_mm": 200.0,
                "rainfall_duration_hours": 4.0,
                "spatial_distribution": "convective_core",
                "catchment_id": "INDOFLOODS-gauge-602",
                "initial_soil_saturation_pct": 80.0,
            },
        }
        resp = client.post("/api/simulation/run", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert "SIM-" in data["simulation_id"]
        sim_id = data["simulation_id"]

        # Test sub-resource endpoints with this id
        resp_get = client.get(f"/api/simulation/{sim_id}")
        assert resp_get.status_code == 200
        assert resp_get.json()["simulation_id"] == sim_id

        resp_inun = client.get(f"/api/simulation/{sim_id}/inundation")
        assert resp_inun.status_code == 200

        resp_pop = client.get(f"/api/simulation/{sim_id}/population-impact")
        assert resp_pop.status_code == 200

        resp_infra = client.get(f"/api/simulation/{sim_id}/infrastructure-impact")
        assert resp_infra.status_code == 200

        resp_tl = client.get(f"/api/simulation/{sim_id}/timeline")
        assert resp_tl.status_code == 200
        assert len(resp_tl.json()["growth_points"]) > 0

    def test_simulation_history_endpoint(self, client):
        resp = client.get("/api/simulation/history?limit=10")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_invalid_simulation_id_404(self, client):
        resp = client.get("/api/simulation/SIM-NONEXISTENT")
        assert resp.status_code == 404

    def test_missing_params_validation_400(self, client):
        # Scenario type rainfall without rainfall_params
        payload = {
            "scenario_type": "rainfall",
            "simulation_period_hours": 6,
        }
        resp = client.post("/api/simulation/run", json=payload)
        assert resp.status_code == 400


# =============================================================================
# 7. System Isolation & Existing Functionality Non-Regression
# =============================================================================

class TestSystemNonRegression:
    """Ensure existing system health and prediction routes remain unaffected."""

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "online"

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_api_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert "System Online" in resp.json()["status"]

    def test_digital_twin_routes_still_operational(self, client):
        resp = client.get("/api/digital-twin/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "online"
