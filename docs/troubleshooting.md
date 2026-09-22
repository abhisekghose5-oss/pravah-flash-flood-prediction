# PRAVAH — Operational Troubleshooting & Maintenance Runbook

**System Version:** 2.5.0  
**Log Prefix:** `pravah.*`  
**Diagnostic URL:** `/api/integration/health`

---

## 1. Quick Diagnostics Checklist

If an anomaly is observed, run the following fast diagnostics:

```bash
# Check overall health and subsystem states
curl -s http://localhost:8000/api/integration/health

# Verify SQLite database connectivity and migrations
python -c "from src.data.migrations import get_migration_status; print(get_migration_status())"

# Verify all ML models loaded in memory
curl -s http://localhost:8000/api/health
```

---

## 2. Common Issues, Root Causes & Resolutions

### 2.1 Issue: `InconsistentVersionWarning` on Scikit-Learn Models
* **Symptom:** Terminal outputs warning: `Trying to unpickle estimator SimpleImputer from version 1.9.0 when using version 1.9.1`.
* **Root Cause:** Serialized model `.joblib` bundles were trained under scikit-learn 1.9.0 while the runtime environment uses 1.9.1.
* **Resolution:** This is benign and does not affect prediction fidelity or model weights. All inference tests pass consistently. To silence warnings in production, `warnings.filterwarnings("ignore", category=UserWarning)` can be enabled.

### 2.2 Issue: Alerts Output `SIM_CALL_...` or `SIM_SMS_...`
* **Symptom:** Outbound alerts do not send physical SMS or dial phones; instead response contains `SIM_SMS_...`.
* **Root Cause:** Environment variables (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`) are not set or left as placeholders.
* **Resolution:** This is intentional **Safe Sandbox Mode** designed to allow zero-cost testing. To enable live cellular dispatch, set valid Twilio credentials in `.env` and restart the API server.

### 2.3 Issue: Open-Meteo Weather Poller Status is `"simulating"`
* **Symptom:** `/api/weather/live` returns `"status": "simulating"`.
* **Root Cause:** Outbound HTTPS connectivity to `api.open-meteo.com` timed out or network proxy blocked port 443.
* **Resolution:**
  1. Test outbound network: `curl -I https://api.open-meteo.com/v1/forecast?latitude=17.2944&longitude=74.1903`.
  2. PRAVAH continues serving the latest cached weather observation or fallback rainfall series without failing inference endpoints.

### 2.4 Issue: SQLite `database is locked` Error
* **Symptom:** High concurrent requests throw `sqlite3.OperationalError: database is locked`.
* **Root Cause:** SQLite write concurrency limit under multiple simultaneous processes.
* **Resolution:**
  1. PRAVAH's `src.data.db.get_connection()` enables WAL (Write-Ahead Logging) mode:
     ```python
     conn.execute("PRAGMA journal_mode=WAL;")
     conn.execute("PRAGMA busy_timeout=5000;")
     ```
  2. WAL mode allows concurrent readers while writes execute sequentially with a 5000ms busy wait timeout.

### 2.5 Issue: XAI Explanation Takes Too Long
* **Symptom:** Latency on `/api/integration/workflow/predict-and-explain` exceeds 500ms.
* **Root Cause:** SHAP `TreeExplainer` calculating exact coalitions on large background dataset.
* **Resolution:**
  1. PRAVAH uses pre-calculated background medoids for fast Shapley evaluation.
  2. To bypass explanation when only raw probability is needed, set `"explain": false` in the request body.

---

## 3. Log Locations & Severity Levels

PRAVAH logs across standard loggers:
* `pravah.api`: Request handling, router mounting, and HTTP errors.
* `pravah.inference`: Model bundle deserialization and feature engineering.
* `pravah.alerts`: Multi-channel dispatch outcomes and delivery receipts.
* `pravah.integration`: Cross-module workflow lifecycle and timing metrics.
* `pravah.gauges`: Hydrometric stage evaluation and rate-of-rise metrics.
