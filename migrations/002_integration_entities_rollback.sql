-- PRAVAH — Rollback Migration 002
-- Safely drops additive integration entities while preserving all baseline telemetry tables.

DROP TABLE IF EXISTS flood_propagation_simulation_records;
DROP TABLE IF EXISTS digital_twin_simulation_records;
DROP TABLE IF EXISTS xai_explanation_records;
DROP TABLE IF EXISTS ivrs_call_records;
DROP TABLE IF EXISTS river_gauge_records;

DELETE FROM schema_migrations WHERE version = '002_integration_entities';
