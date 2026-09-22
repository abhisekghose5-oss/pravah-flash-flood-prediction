-- PRAVAH — Baseline Database Schema Snapshot (Migration 001)
-- Documents existing pre-consolidation telemetry and operational tables.

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    catchment_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sub_catchment ON subscriptions(catchment_id);

CREATE TABLE IF NOT EXISTS sos_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    severity TEXT NOT NULL,
    severity_tier TEXT,
    landmark_notes TEXT,
    timestamp TEXT NOT NULL,
    region_tag TEXT
);
CREATE INDEX IF NOT EXISTS idx_sos_coords ON sos_reports(latitude, longitude);

CREATE TABLE IF NOT EXISTS relief_shelters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shelter_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    location_name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    capacity INTEGER NOT NULL,
    current_occupancy INTEGER DEFAULT 0,
    elevation_m REAL,
    contact_phone TEXT,
    status TEXT DEFAULT 'ACCEPTING',
    region TEXT DEFAULT 'Maharashtra',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_shelter_region ON relief_shelters(region);
CREATE INDEX IF NOT EXISTS idx_shelter_coords ON relief_shelters(latitude, longitude);

CREATE TABLE IF NOT EXISTS community_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT UNIQUE NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    location_name TEXT NOT NULL,
    region TEXT DEFAULT 'Maharashtra',
    hazard_type TEXT NOT NULL,
    water_depth_m REAL,
    impact_severity TEXT NOT NULL,
    description TEXT NOT NULL,
    reporter_role TEXT NOT NULL,
    reporter_contact TEXT,
    photo_urls TEXT DEFAULT '[]',
    verification_status TEXT DEFAULT 'PENDING',
    verification_notes TEXT,
    verified_by TEXT,
    parent_alert_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comm_coords ON community_reports(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_comm_type ON community_reports(hazard_type);
CREATE INDEX IF NOT EXISTS idx_comm_status ON community_reports(verification_status);
CREATE INDEX IF NOT EXISTS idx_comm_reported ON community_reports(created_at);
CREATE INDEX IF NOT EXISTS idx_comm_parent ON community_reports(parent_alert_code);

CREATE TABLE IF NOT EXISTS multi_channel_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_code TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    location TEXT NOT NULL,
    region TEXT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    trigger_reason TEXT NOT NULL,
    risk_score REAL,
    river_level REAL,
    river_threshold REAL,
    rainfall_forecast REAL,
    evacuation_route TEXT,
    shelter_location TEXT,
    overall_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alert_ts ON multi_channel_alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alert_sev ON multi_channel_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alert_loc ON multi_channel_alerts(location);

CREATE TABLE IF NOT EXISTS alert_channel_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    delivery_status TEXT NOT NULL,
    provider_message_id TEXT,
    error_message TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(alert_id) REFERENCES multi_channel_alerts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_delivery_alert ON alert_channel_deliveries(alert_id);
CREATE INDEX IF NOT EXISTS idx_delivery_chan ON alert_channel_deliveries(channel);

CREATE TABLE IF NOT EXISTS evacuation_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_code TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    origin_lat REAL NOT NULL,
    origin_lng REAL NOT NULL,
    destination_shelter_id TEXT NOT NULL,
    objective TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    distance_km REAL NOT NULL,
    travel_time_minutes REAL NOT NULL,
    risk_score REAL NOT NULL,
    route_status TEXT NOT NULL,
    waypoints_json TEXT NOT NULL,
    instructions_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evac_route_created ON evacuation_routes(created_at);
