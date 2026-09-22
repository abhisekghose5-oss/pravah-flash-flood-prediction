-- PRAVAH — Additive Migration 002: System Consolidation & Entity Persistence
-- Adds persistent tables for River Gauges, IVRS Outbound Calls, XAI Explanations,
-- Digital Twin Runoff Simulations, and Flood Propagation History.

-- 1. Migration Version Tracking Table
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

-- 2. River Gauge Records & Observations Table
CREATE TABLE IF NOT EXISTS river_gauge_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gauge_id TEXT NOT NULL,
    station_name TEXT NOT NULL,
    river_name TEXT NOT NULL,
    basin_name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    current_level_m REAL NOT NULL,
    warning_level_m REAL NOT NULL,
    danger_level_m REAL NOT NULL,
    status TEXT NOT NULL,
    trend_24h TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gauge_id ON river_gauge_records(gauge_id);
CREATE INDEX IF NOT EXISTS idx_gauge_status ON river_gauge_records(status);
CREATE INDEX IF NOT EXISTS idx_gauge_recorded ON river_gauge_records(recorded_at);

-- 3. IVRS Voice Call Logs Table
CREATE TABLE IF NOT EXISTS ivrs_call_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT UNIQUE NOT NULL,
    recipient_phone TEXT NOT NULL,
    alert_code TEXT,
    severity TEXT NOT NULL,
    call_status TEXT NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    audio_url TEXT,
    speech_script TEXT NOT NULL,
    provider_call_sid TEXT,
    timestamp_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ivrs_call_id ON ivrs_call_records(call_id);
CREATE INDEX IF NOT EXISTS idx_ivrs_status ON ivrs_call_records(call_status);
CREATE INDEX IF NOT EXISTS idx_ivrs_ts ON ivrs_call_records(timestamp_utc);

-- 4. Explainable AI (XAI) Execution Metadata Table
CREATE TABLE IF NOT EXISTS xai_explanation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    explanation_id TEXT UNIQUE NOT NULL,
    model_name TEXT NOT NULL,
    gauge_id TEXT NOT NULL,
    predicted_risk REAL NOT NULL,
    alert_tier TEXT NOT NULL,
    top_feature_1 TEXT,
    top_feature_1_shap REAL,
    top_feature_2 TEXT,
    top_feature_2_shap REAL,
    top_feature_3 TEXT,
    top_feature_3_shap REAL,
    execution_time_ms REAL,
    timestamp_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_xai_gauge ON xai_explanation_records(gauge_id);
CREATE INDEX IF NOT EXISTS idx_xai_model ON xai_explanation_records(model_name);
CREATE INDEX IF NOT EXISTS idx_xai_ts ON xai_explanation_records(timestamp_utc);

-- 5. Digital Twin Hydrological Simulation Audit Table
CREATE TABLE IF NOT EXISTS digital_twin_simulation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id TEXT UNIQUE NOT NULL,
    watershed_id TEXT NOT NULL,
    watershed_name TEXT NOT NULL,
    rainfall_mm REAL NOT NULL,
    duration_hours REAL NOT NULL,
    moisture_condition TEXT NOT NULL,
    peak_runoff_rate_m3s REAL NOT NULL,
    runoff_volume_m3 REAL NOT NULL,
    high_accumulation_area_km2 REAL NOT NULL,
    execution_time_ms REAL,
    timestamp_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dt_watershed ON digital_twin_simulation_records(watershed_id);
CREATE INDEX IF NOT EXISTS idx_dt_ts ON digital_twin_simulation_records(timestamp_utc);

-- 6. Flood Propagation & Inundation Simulation Audit Table
CREATE TABLE IF NOT EXISTS flood_propagation_simulation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id TEXT UNIQUE NOT NULL,
    scenario_type TEXT NOT NULL,
    scenario_title TEXT NOT NULL,
    target_region TEXT NOT NULL,
    simulation_period_hours INTEGER NOT NULL,
    max_extent_km2 REAL NOT NULL,
    peak_depth_m REAL NOT NULL,
    total_population_impacted INTEGER NOT NULL,
    roads_submerged_km REAL NOT NULL,
    bridges_submerged_count INTEGER NOT NULL,
    execution_time_ms REAL,
    timestamp_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fps_sim_id ON flood_propagation_simulation_records(simulation_id);
CREATE INDEX IF NOT EXISTS idx_fps_scen_type ON flood_propagation_simulation_records(scenario_type);
CREATE INDEX IF NOT EXISTS idx_fps_ts ON flood_propagation_simulation_records(timestamp_utc);
