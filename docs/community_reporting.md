# PRAVAH — Community Reporting & Crowdsourced Flood Intelligence Module

## 1. Executive Summary & Architectural Overview

The **Community Reporting & Crowdsourced Flood Intelligence Module** enhances PRAVAH's situational awareness by capturing ground-level observations directly from citizens, volunteers, and emergency first-responders. It operates as an **independent, modular, backward-compatible subsystem** that feeds ground truth into the flood monitoring lifecycle without altering existing AI prediction models or core alerting thresholds.

```text
                               CITIZEN / VOLUNTEER
                                        │
                                        ▼
                 ┌──────────────────────────────────────────────┐
                 │  Emergency Citizen Report Interface          │
                 │  • Photo Evidence Upload (JPEG/PNG/WebP)     │
                 │  • Automatic GPS / Mini-Map Pin Selector     │
                 │  • 4 Report Types (Flood, Road, Gauge, Other)│
                 └──────────────────────┬───────────────────────┘
                                        │ (HTTP POST / Multipart)
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                      src/community/ Backend Module                            │
│                                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────────┐ │
│  │  report_validation   │  │    photo_service     │  │  duplicate_service  │ │
│  │  • Coordinate bounds │  │  • Magic byte verify │  │  • Haversine ≤ 1 km │ │
│  │  • XSS sanitization  │  │  • UUID randomization│  │  • Δt ≤ 2.0 hours   │ │
│  │  • Field schema rule │  │  • Max 10MB guard    │  │  • Parent incident  │ │
│  └──────────┬───────────┘  └──────────┬───────────┘  └──────────┬──────────┘ │
│             │                         │                         │            │
│             └─────────────────────────┼─────────────────────────┘            │
│                                       ▼                                      │
│                      ┌─────────────────────────────────┐                     │
│                      │    report_service (SQLite)      │                     │
│                      │    data/pravah_telemetry.db     │                     │
│                      │    Table: community_reports     │                     │
│                      └────────────────┬────────────────┘                     │
│                                       │                                      │
│                     ┌─────────────────┴─────────────────┐                    │
│                     ▼                                   ▼                    │
│         ┌───────────────────────┐           ┌──────────────────────┐         │
│         │   moderation_service  │           │intelligence_pipeline │         │
│         │   Status Lifecycle:   │           │• Ground truth signals│         │
│         │   SUBMITTED ->        │           │• Confidence scoring  │         │
│         │   PENDING_REVIEW ->   │           │• Escalation advisory │         │
│         │   VERIFIED / REJECTED │           └──────────┬───────────┘         │
│         │   -> RESOLVED         │                      │                     │
│         └───────────────────────┘                      │                     │
└────────────────────────────────────────────────────────┼─────────────────────┘
                                                         │
                                    ┌────────────────────┴─────────────────────┐
                                    ▼                                          ▼
                      ┌───────────────────────────┐              ┌───────────────────────────┐
                      │ Community Reports Portal  │              │ PRAVAH AI Inference Engine│
                      │ (`community.html`)        │              │ (Decoupled Integration    │
                      │ • Live GIS Leaflet Map    │              │  via `/api/community/     │
                      │ • Real-time KPI Cards     │              │  signals`)                │
                      │ • Search & Moderation     │              └───────────────────────────┘
                      └───────────────────────────┘
```

---

## 2. Directory Structure

```text
src/community/
├── __init__.py
├── community_manager.py         # Orchestration facade
├── report_service.py            # SQLite data persistence & GeoJSON generator
├── report_validation.py         # Coordinate, XSS, and schema validation
├── models/
│   ├── __init__.py
│   └── incident.py              # Pydantic schemas & enums
├── routes/
│   ├── __init__.py
│   └── community_routes.py      # FastAPI REST router mounted at /api/community
├── services/
│   ├── __init__.py
│   ├── photo_service.py         # Magic byte & file upload security
│   ├── geolocation_service.py   # Distance calculation & gauge proximity
│   ├── duplicate_service.py     # Spatial-temporal incident clustering
│   ├── moderation_service.py    # State lifecycle transition engine
│   └── intelligence_pipeline.py # Ground-truth confidence synthesis
└── utils/
    ├── __init__.py
    └── helpers.py               # Anonymization, sanitization, and ID formatting
```

---

## 3. Supported Report Types

| Type Identifier | User Category | Key Attributes | Example |
| :--- | :--- | :--- | :--- |
| `FLOOD_OBSERVATION` | General Flooding | Approximate water depth (m), severity tier, observed conditions | Mahad market square submerged under 1.2m of river water |
| `BLOCKED_ROAD` | Passability Hazard | Road name (e.g. NH-48), passability status (`OPEN`, `PARTIALLY_BLOCKED`, `COMPLETELY_BLOCKED`), hazard cause (landslide, flood overtopping, trees) | NH-48 Wai bypass completely blocked by 0.8m fast-moving water |
| `WATER_LEVEL` | Citizen Gauge Reading | Observed water level (m), bridge benchmark indicator | Observed watermark at Beki railway bridge pier reached 2.4m |
| `GENERAL_INCIDENT` | Critical Infrastructure | Hazard cause, infrastructure damage, stranded persons | Brahmaputra embankment scouring near Dibrugarh link road |

---

## 4. Photo Security Architecture

Uploaded photographs are rigorously sanitized and protected against malicious payloads:
1. **Extension Whitelist**: Only `.jpg`, `.jpeg`, `.png`, and `.webp` files are accepted.
2. **MIME Verification**: Inspects `content-type` against `image/jpeg`, `image/png`, and `image/webp`.
3. **Magic Byte Inspection**: Validates binary headers directly in memory:
   - JPEG: `\xff\xd8\xff`
   - PNG: `\x89PNG\r\n\x1a\n`
   - WEBP: `RIFF....WEBP`
   Disguised executable binaries (e.g. `.exe`, `.sh`, `.php`) are rejected immediately with HTTP 400.
4. **Size Limitation**: Configurable via `MAX_REPORT_IMAGE_SIZE` environment variable (default: `10 * 1024 * 1024` = 10 MB).
5. **UUID Randomization**: Files are saved as `{uuid4().hex}{ext}` in `data/uploads/community_photos/`.
6. **Path Traversal Protection**: Client filenames are never used as filesystem paths.
7. **Privacy Preservation**: Internal file paths are never returned. Instead, relative paths `/uploads/community_photos/{uuid}.jpg` are served via FastAPI's static mount.

---

## 5. Geolocation & Geofencing

- **Coordinate Guardrails**: Validates finite real numbers within valid latitudes `[-90, 90]` and longitudes `[-180, 180]`. Null Island coordinates `(0, 0)` are explicitly rejected.
- **Dual-Basin Classification**: Heuristically detects if reports originate within the **Maharashtra Western Ghats** (`15.0°N–22.5°N, 72.0°E–81.0°E`) or the **Northeast Brahmaputra Basin** (`23.5°N–29.5°N, 88.5°E–98.0°E`).
- **Telemetry Gauge Proximity Correlation**: Automatically identifies the closest official PRAVAH CWC gauge station (e.g. Karad, Mahad, Beki, Dibrugarh) using Haversine calculation to give emergency dispatchers immediate river-basin context.

---

## 6. Duplicate Detection & Incident Clustering

When multiple citizens report the same emergency event, PRAVAH preserves each citizen submission while clustering them under a single parent incident:
- **Spatial Radius**: $\le 1.0\text{ km}$ Haversine distance.
- **Temporal Window**: $\le 2.0\text{ hours}$.
- **Category Match**: Matching `report_type`.
- **Clustering Behavior**:
  - The first report becomes the parent (`parent_incident_id = NULL`).
  - Subsequent submissions within the window point to `parent_incident_id`.
  - Accessible via `GET /api/community/clusters` to visualize incident density.

---

## 7. Moderation Lifecycle

```text
SUBMITTED ──► PENDING_REVIEW ──► VERIFIED ──► RESOLVED
                     │               ▲
                     ▼               │
                  REJECTED ──────────┘
```

- Every crowdsourced submission enters the queue as `PENDING_REVIEW` (`is_verified = False`).
- Emergency dispatchers review evidence and transition reports via `PATCH /api/community/reports/{id}/status`.
- Only reports with status `VERIFIED` are marked `is_verified = True` and fed into ground-truth intelligence signals.

---

## 8. REST API Specification

All endpoints are mounted under `/api/community`:

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/community/reports` | Submit report via JSON payload (`CommunityReportCreate`) |
| `POST` | `/api/community/reports/multipart` | Submit report with photo upload via `multipart/form-data` |
| `GET` | `/api/community/reports` | Retrieve filtered reports (query params: `report_type`, `severity`, `status`, `region`, `search`, `limit`, `offset`) |
| `GET` | `/api/community/reports/{id}` | Fetch single report details with cluster sibling count |
| `PATCH` | `/api/community/reports/{id}/status` | Update lifecycle status (`PENDING_REVIEW`, `VERIFIED`, `REJECTED`, `RESOLVED`) |
| `POST` | `/api/community/reports/{id}/photos` | Upload additional photographic evidence to an existing report |
| `GET` | `/api/community/reports/map` | Standard GeoJSON FeatureCollection for GIS map rendering |
| `GET` | `/api/community/stats` | KPI aggregate statistics for dashboard summary cards |
| `GET` | `/api/community/clusters` | Grouped spatial-temporal incident clusters |
| `GET` | `/api/community/signals` | Ground-truth intelligence signals for downstream AI models |

---

## 9. Database Schema (`data/pravah_telemetry.db`)

```sql
CREATE TABLE IF NOT EXISTS community_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_code TEXT UNIQUE NOT NULL,           -- e.g. 'CR-1001'
    report_type TEXT NOT NULL,                  -- 'FLOOD_OBSERVATION', 'BLOCKED_ROAD', etc.
    title TEXT,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,                     -- 'LOW', 'MODERATE', 'HIGH', 'CRITICAL'
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    location_accuracy REAL,
    location_name TEXT,
    district TEXT,
    state_region TEXT,
    water_depth REAL,
    road_status TEXT,                           -- 'OPEN', 'PARTIALLY_BLOCKED', 'COMPLETELY_BLOCKED', 'UNKNOWN'
    road_name TEXT,
    hazard_cause TEXT,
    photo_url TEXT,
    additional_photos TEXT,                     -- JSON array of photo URLs
    reported_at TEXT NOT NULL,
    reporter_id TEXT,
    reporter_name TEXT,
    reporter_contact TEXT,                      -- Protected / Masked PII
    verification_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    moderator_notes TEXT,
    parent_incident_id INTEGER,
    is_duplicate INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_comm_coords ON community_reports(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_comm_type ON community_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_comm_status ON community_reports(verification_status);
CREATE INDEX IF NOT EXISTS idx_comm_reported ON community_reports(reported_at);
CREATE INDEX IF NOT EXISTS idx_comm_parent ON community_reports(parent_incident_id);
```

---

## 10. Downstream Intelligence Integration

The module exposes `GET /api/community/signals` and `compute_community_ground_signals()`.
- Queries verified reports in the vicinity of any coordinate or catchment.
- Computes ground-truth confidence scores (0.00 to 1.00) based on verified hazard density.
- Can be ingested by the PRAVAH dashboard or alert dispatchers without touching the ML model pipelines.
