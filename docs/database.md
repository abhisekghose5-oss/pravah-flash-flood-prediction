# PRAVAH — Database Schema & Migration Architecture

**Database Engine:** SQLite 3  
**Database File:** `data/pravah_telemetry.db`  
**Migration Directory:** `migrations/`  
**Migration Tooling:** `src/data/migrations.py`

---

## 1. Schema Migration Management

PRAVAH employs an additive, forward-only, and fully reversible migration tracking engine managed by the `schema_migrations` catalog table.

### 1.1 Migration Catalog (`schema_migrations`)

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);
```

### 1.2 Migration Inventory

| Version | File | Description | Type |
|---|---|---|---|
| `001_initial_schema` | `migrations/001_initial_schema.sql` | Documents baseline existing tables (subscriptions, SOS, relief shelters, alert logs, evacuation routes). | Baseline |
| `002_integration_entities` | `migrations/002_integration_entities.sql` | Creates additive entities: `river_gauge_records`, `ivrs_call_records`, `xai_explanation_records`, `digital_twin_simulation_records`, `flood_propagation_simulation_records`. | Additive |
| `002_rollback` | `migrations/002_integration_entities_rollback.sql` | Safe rollback script removing additive entities without touching baseline tables. | Rollback |

---

## 2. Table Specifications

### 2.1 Baseline Tables (Existing)

1. **`subscriptions`**: Community notification phone numbers, notification channels, registered regions.
2. **`sos_reports`**: Direct citizen SOS emergency pings, GPS coordinates, rescue status.
3. **`relief_shelters`**: Designated emergency shelters, location lat/lng, bed capacity, supplies status.
4. **`community_reports`**: Crowdsourced flood observations, water depth categories, photo uploads.
5. **`multi_channel_alerts`**: High-level alert records, risk scores, locations, timestamp.
6. **`alert_channel_deliveries`**: Individual per-channel delivery attempts, status codes, external provider IDs.
7. **`evacuation_routes`**: Generated safe evacuation path geometries, travel times, destination shelters.

### 2.2 Additive Integration Entities

#### `river_gauge_records`
Logs hydrometric observations, warning/danger threshold checks, and 24-hour rate of rise.
```sql
CREATE TABLE IF NOT EXISTS river_gauge_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    gauge_id VARCHAR(64) NOT NULL,
    station_name VARCHAR(128) NOT NULL,
    river_name VARCHAR(128),
    region VARCHAR(64) DEFAULT 'Maharashtra',
    stage_level_m REAL NOT NULL,
    warning_level_m REAL NOT NULL,
    danger_level_m REAL NOT NULL,
    status VARCHAR(32) NOT NULL,
    rate_of_rise_m_hr REAL DEFAULT 0.0,
    observation_source VARCHAR(64) DEFAULT 'TELEMETRY',
    timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `ivrs_call_records`
Stores voice dispatch outcomes, speech synthesis scripts, and call durations.
```sql
CREATE TABLE IF NOT EXISTS ivrs_call_records (
    call_id VARCHAR(64) PRIMARY KEY,
    recipient_phone VARCHAR(32) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    location VARCHAR(128),
    script_text TEXT NOT NULL,
    call_status VARCHAR(32) NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    provider VARCHAR(32) DEFAULT 'TWILIO_VOICE',
    created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `xai_explanation_records`
Audits Explainable AI (SHAP) feature attributions.
```sql
CREATE TABLE IF NOT EXISTS xai_explanation_records (
    explanation_id VARCHAR(64) PRIMARY KEY,
    model_name VARCHAR(64) NOT NULL,
    gauge_id VARCHAR(64) NOT NULL,
    predicted_risk REAL NOT NULL,
    alert_tier VARCHAR(32) NOT NULL,
    top_feature_1 VARCHAR(64),
    top_feature_1_shap REAL,
    top_feature_2 VARCHAR(64),
    top_feature_2_shap REAL,
    top_feature_3 VARCHAR(64),
    top_feature_3_shap REAL,
    execution_time_ms REAL,
    timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `digital_twin_simulation_records`
Logs SCS-CN runoff computations and elevation profiles.
```sql
CREATE TABLE IF NOT EXISTS digital_twin_simulation_records (
    simulation_id VARCHAR(64) PRIMARY KEY,
    watershed_id VARCHAR(64) NOT NULL,
    catchment_name VARCHAR(128),
    rainfall_input_mm REAL NOT NULL,
    runoff_volume_m3 REAL NOT NULL,
    peak_discharge_m3s REAL NOT NULL,
    time_of_concentration_hr REAL,
    soil_curve_number REAL,
    timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `flood_propagation_simulation_records`
Captures hydrodynamic scenario outputs and infrastructure exposure assessments.
```sql
CREATE TABLE IF NOT EXISTS flood_propagation_simulation_records (
    simulation_id VARCHAR(64) PRIMARY KEY,
    scenario_type VARCHAR(32) NOT NULL,
    scenario_title VARCHAR(128) NOT NULL,
    target_region VARCHAR(64) NOT NULL,
    simulation_period_hours INTEGER NOT NULL,
    max_extent_km2 REAL NOT NULL,
    peak_depth_m REAL NOT NULL,
    total_population_impacted INTEGER DEFAULT 0,
    roads_submerged_km REAL DEFAULT 0.0,
    bridges_submerged_count INTEGER DEFAULT 0,
    execution_time_ms REAL,
    timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Migration Runner CLI

PRAVAH provides an automated Python CLI for schema verification, forward migration, and rollback testing:

### Apply Pending Migrations
```bash
python -m src.data.migrations
```
*Output:*
```text
[MIGRATIONS] Applying pending database migrations...
  ✓ Migration '001_initial_schema' applied successfully.
  ✓ Migration '002_integration_entities' applied successfully.
[MIGRATIONS] Database schema is up to date (2 applied, 0 pending).
```

### Check Migration Status
```python
from src.data.migrations import get_migration_status
status = get_migration_status()
print(status)
# {'applied_count': 2, 'pending_count': 0, 'applied_versions': ['001_initial_schema', '002_integration_entities']}
```

### Revert Migration (Rollback)
```python
from src.data.migrations import rollback_migration
rollback_migration("002_integration_entities")
```
Reverts all additive tables while preserving all baseline tables and data.
