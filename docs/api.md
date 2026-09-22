# PRAVAH — Comprehensive REST API Specification

**Version:** 2.5.0  
**Base URL:** `http://localhost:8000`  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI) or `/redoc` (ReDoc)

---

## 1. System & Unified Health Endpoints

### 1.1 Live System Diagnostic Check
* **Method:** `GET`
* **Path:** `/api/health`
* **Description:** Returns primary ML model memory status, Open-Meteo connectivity, and catchment count. Fully backward-compatible.
* **Response `200 OK`:**
```json
{
  "status": "System Online",
  "model_loaded": true,
  "data_api_reachable": true,
  "available_models": [
    "task_a_onset_RandomForest",
    "task_a_onset_XGBoost",
    "task_a_onset_LightGBM",
    "task_b_active_RandomForest",
    "task_b_active_XGBoost",
    "task_b_active_LightGBM"
  ],
  "total_catchments": 20,
  "total_northeast_stations": 46,
  "active_regions": ["Maharashtra Western Ghats", "Northeast India (Brahmaputra Basin)"],
  "timestamp": "2026-09-22T15:20:00.000000+00:00"
}
```

### 1.2 Unified Subsystems Health
* **Method:** `GET`
* **Path:** `/api/integration/health`
* **Description:** Comprehensive operational health across all 9 platform subsystems and the persistence database.
* **Response `200 OK`:**
```json
{
  "platform": "PRAVAH Flood Intelligence Platform",
  "version": "2.5.0",
  "overall_status": "HEALTHY",
  "timestamp_utc": "2026-09-22T15:20:00.000000+00:00",
  "subsystems": {
    "river_gauge_monitoring": {"status": "ONLINE", "gauges_count": 66},
    "sms_alert_channel": {"status": "ONLINE", "mode": "sandbox"},
    "whatsapp_alert_channel": {"status": "ONLINE", "mode": "sandbox"},
    "telegram_alert_channel": {"status": "ONLINE", "mode": "sandbox"},
    "ivrs_calling_channel": {"status": "ONLINE", "mode": "sandbox"},
    "evacuation_planning_engine": {"status": "ONLINE", "shelters_active_count": 10},
    "explainable_ai_engine": {"status": "ONLINE", "framework": "SHAP TreeExplainer"},
    "digital_twin_studio": {"status": "ONLINE", "hydrology_model": "SCS-CN Runoff & Elevation DEM"},
    "flood_propagation_simulator": {"status": "ONLINE"},
    "persistence_database": {"status": "HEALTHY", "engine": "SQLite 3", "migrations_applied": 2}
  }
}
```

---

## 2. River Gauge Monitoring Endpoints (`/api/gauges`)

### 2.1 List All River Gauges
* **Method:** `GET`
* **Path:** `/api/gauges`
* **Query Parameters:**
  * `region` (optional): Filter by `'Maharashtra'` or `'Northeast'`
  * `status` (optional): Filter by `'NORMAL'`, `'WARNING'`, or `'DANGER'`
* **Response `200 OK`:** Array of `RiverGauge` objects.

### 2.2 Get Specific River Gauge Telemetry
* **Method:** `GET`
* **Path:** `/api/gauges/{gauge_id}`
* **Example:** `/api/gauges/684` or `/api/gauges/NE-Beki`
* **Response `200 OK`:**
```json
{
  "gauge_id": "INDOFLOODS-gauge-684",
  "clean_id": "684",
  "station_name": "Karad",
  "river_name": "Krishna",
  "basin": "Krishna",
  "region": "Maharashtra",
  "latitude": 17.289,
  "longitude": 74.181,
  "current_level_m": 7.45,
  "warning_level_m": 8.0,
  "danger_level_m": 10.5,
  "status": "NORMAL",
  "trend_24h": "STABLE",
  "rate_of_rise_m_hr": 0.05,
  "last_updated": "2026-09-22T15:20:00+00:00"
}
```

### 2.3 Post Live Gauge Observation
* **Method:** `POST`
* **Path:** `/api/gauges/{gauge_id}/observe`
* **Request Body:**
```json
{
  "current_level_m": 9.20,
  "discharge_m3s": 1250.0,
  "observer_notes": "Heavy upstream runoff observed at Karad bridge."
}
```
* **Response `200 OK`:** Evaluates warning/danger marks and returns stage status (`WARNING`, `DANGER`).

---

## 3. IVRS Voice Calling Endpoints (`/api/ivrs`)

### 3.1 Initiate Emergency IVRS Call
* **Method:** `POST`
* **Path:** `/api/ivrs/call`
* **Request Body:**
```json
{
  "to_phone": "+919876543210",
  "location": "Karad River Basin",
  "severity": "CRITICAL",
  "risk_score": 88.5,
  "evacuation_route": "SH-72 via High Ridge",
  "shelter_name": "Karad Elevated Relief Center"
}
```
* **Response `200 OK`:**
```json
{
  "call_id": "SIM_CALL_4B8A12F9",
  "status": "QUEUED",
  "to_phone": "+919876543210",
  "severity": "CRITICAL",
  "script_text": "Emergency notification from the PRAVAH flood early warning network. Critical flood danger detected for Karad River Basin...",
  "timestamp_utc": "2026-09-22T15:20:00.000000+00:00"
}
```

### 3.2 Get IVRS Call Telemetry
* **Method:** `GET`
* **Path:** `/api/ivrs/status/{call_id}`

### 3.3 List IVRS Call History
* **Method:** `GET`
* **Path:** `/api/ivrs/calls?limit=20`

---

## 4. Platform Integration Workflows (`/api/integration/workflow`)

### 4.1 River Gauge Threshold Breach & Alert Dispatch
* **Method:** `POST`
* **Path:** `/api/integration/workflow/river-threshold-alert`
* **Request Body:**
```json
{
  "gauge_id": "684",
  "simulated_level_m": 11.2,
  "channels": ["sms", "whatsapp", "telegram", "ivrs"],
  "custom_recipient": "+919876543210"
}
```
* **Response `200 OK`:**
```json
{
  "workflow": "river_gauge_threshold_alert",
  "status": "ALERT_TRIGGERED",
  "alert_triggered": true,
  "gauge_evaluation": {
    "gauge_id": "684",
    "status": "DANGER",
    "current_level_m": 11.2,
    "warning_level_m": 8.0,
    "danger_level_m": 10.5,
    "threshold_exceeded": true,
    "alert_severity": "EVACUATION"
  },
  "alert_dispatch": {
    "alert_id": "c1f7a40b-789a-4c22-b651-4091ab7e90c8",
    "channels_dispatched": ["sms", "whatsapp", "telegram", "ivrs"],
    "deliveries": {
      "sms": {"status": "SIMULATED", "message_id": "SIM_SMS_9381A"},
      "whatsapp": {"status": "SIMULATED", "message_id": "SIM_WA_B1902"},
      "telegram": {"status": "SIMULATED", "message_id": "SIM_TG_88421"},
      "ivrs": {"status": "SIMULATED", "message_id": "SIM_CALL_41872"}
    }
  },
  "timestamp_utc": "2026-09-22T15:20:00.000000+00:00"
}
```

### 4.2 ML Flood Prediction & Explainable AI (SHAP)
* **Method:** `POST`
* **Path:** `/api/integration/workflow/predict-and-explain`
* **Request Body:**
```json
{
  "gauge_id": "684",
  "rainfall_history_10d": [10.5, 12.0, 18.5, 25.0, 42.0, 65.0, 88.0, 115.0, 140.0, 155.0],
  "onset_model": "RandomForest",
  "active_model": "XGBoost",
  "explain": true
}
```
* **Response `200 OK`:**
```json
{
  "workflow": "predict_and_explain",
  "prediction": {
    "onset_probability": 0.884,
    "onset_predicted": true,
    "active_probability": 0.762,
    "active_predicted": true,
    "alert_tier": "EMERGENCY"
  },
  "xai_status": "SUCCESS",
  "xai_explanation": {
    "headline_narrative": "High flood onset risk (88.4%) driven by extreme antecedent rainfall (3-day total: 410.0mm).",
    "top_positive_features": [
      {"feature_name": "rain_3d_sum", "shap_value": 0.342, "actual_value": 410.0},
      {"feature_name": "rain_1d", "shap_value": 0.215, "actual_value": 155.0}
    ],
    "top_negative_features": [
      {"feature_name": "slope", "shap_value": -0.045, "actual_value": 0.052}
    ]
  },
  "execution_time_ms": 142.5
}
```

### 4.3 Simulation-to-Evacuation Planning
* **Method:** `POST`
* **Path:** `/api/integration/workflow/simulation-to-evacuation`
* **Request Body:**
```json
{
  "origin_lat": 17.289,
  "origin_lng": 74.181,
  "preferred_objective": "lowest_risk",
  "scenario_type": "rainfall",
  "simulation_period_hours": 6,
  "rainfall_mm": 135.0,
  "catchment_id": "684"
}
```

### 4.4 End-to-End Disaster Response Lifecycle
* **Method:** `POST`
* **Path:** `/api/integration/workflow/end-to-end`
* **Request Body:**
```json
{
  "gauge_id": "684",
  "rainfall_10d": [12.0, 15.0, 20.0, 35.0, 50.0, 65.0, 80.0, 110.0, 140.0, 160.0],
  "recipient_phone": "+919876543210",
  "channels": ["sms", "whatsapp", "telegram", "ivrs"]
}
```
* **Description:** Runs complete 6-stage lifecycle:
  1. River Gauge Telemetry Check
  2. ML Flood Prediction (Task A & Task B)
  3. Explainable AI (SHAP attributions)
  4. Flood Propagation Simulation (6h convective wave)
  5. Safe Evacuation Route Generation (Dijkstra Lowest-Risk)
  6. Multi-Channel Emergency Dispatch (SMS + WhatsApp + Telegram + IVRS)
