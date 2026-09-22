# PRAVAH — Multi-Channel Alerting System Module

## 1. Executive Summary & Architectural Overview

The **Multi-Channel Alerting System** provides an independent, modular, and resilient emergency early-warning distribution engine for the PRAVAH platform. The system coordinates automated hazard triggers across hydrological sensor thresholds, ML risk assessments, and meteorological forecasts, simultaneously dispatching formatted emergency bulletins across three ubiquitous communication channels:

1. **SMS Cellular Gateway**: Concise, high-reliability text messages (< 160 characters) reaching basic mobile handsets in remote and zero-data rural environments.
2. **WhatsApp Cloud API**: Rich, bold markdown alerts featuring emergency icons, real-time catchment statistics, actionable safety protocols, and helpline coordinates.
3. **Telegram Bot API**: HTML-formatted instant broadcasts dispatching directly to emergency operations channels, disaster management groups, and volunteer networks.

The module is strictly additive and backward-compatible. It leaves all existing prediction models, hydrological simulation engines, and single-channel alerting pathways (`POST /api/alerts/send`) completely intact.

```text
               HAZARD DETECTION & TRIGGER SOURCES
   ┌───────────────────────┬───────────────────────┬───────────────────────┐
   │    ML Risk Score      │   Hydrological Level  │  Doppler Rain Forecast│
   │      (Risk > 70%)     │  (River > 8.0m / 9.0m)│   (Rainfall >= 150mm) │
   └───────────┬───────────┴───────────┬───────────┴───────────┬───────────┘
               │                       │                       │
               └───────────────────────┼───────────────────────┘
                                       ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                  AlertManager Central Orchestrator                      │
 │                                                                         │
 │  ┌───────────────────────┐   ┌───────────────────┐   ┌───────────────┐  │
 │  │   alert_rules.py      │   │alert_templates.py │   │ Cooldown &    │  │
 │  │   Threshold & Severity│──>│SMS, WhatsApp &    │──>│ Escalation    │  │
 │  │   Evaluation Engine   │   │Telegram Formatters│   │ Guard (15 min)│  │
 │  └───────────────────────┘   └───────────────────┘   └───────┬───────┘  │
 │                                                              │          │
 │                      ┌───────────────────────────────────────┘          │
 │                      ▼                                                  │
 │           Concurrent Fault-Isolated Dispatch (asyncio.gather)           │
 └──────────────────────┬───────────────────┬───────────────────┬──────────┘
                        │                   │                   │
         ┌──────────────┴──────┐     ┌──────┴────────┐   ┌──────┴────────┐
         ▼                     ▼     ▼               ▼   ▼               ▼
 ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
 │  SMS Channel  │     │ WhatsApp Cloud│     │ Telegram Bot  │
 │• Twilio Gateway│    │• Meta API /   │     │• Bot API      │
 │• Sandbox Fall-│     │  Twilio WA    │     │  @PravahBot   │
 │  back Mode    │     │• Sandbox Demo │     │• Sandbox Demo │
 └───────┬───────┘     └───────┬───────┘     └───────┬───────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               ▼
        ┌─────────────────────────────────────────────────┐
        │        SQLite Persistence & Audit Trail         │
        │          (data/pravah_telemetry.db)             │
        │  • multi_channel_alerts                         │
        │  • alert_channel_deliveries                     │
        └──────────────────────┬──────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│ Alerts Center Dashboard       │   │ Legacy API Compatibility      │
│ (`alerts.html`)               │   │ `POST /api/alerts/send`       │
│ • Live KPI & Gateway Health   │   │ (Preserved 100% untouched for │
│ • History Table & Filters     │   │  existing integration tests)  │
│ • Interactive Trigger Modal   │   └───────────────────────────────┘
└───────────────────────────────┘
```

---

## 2. Directory Structure & Module Design

All multi-channel alerting logic resides in `src/alerts/`, organized as a decoupled package:

```text
src/alerts/
├── __init__.py                  # Package exports and public entrypoints
├── alert_manager.py             # Central orchestrator: evaluation, cooldown, concurrent dispatch
├── alert_rules.py               # Evaluation logic: Risk > 70%, River Levels, Heavy Rainfall
├── alert_templates.py           # Standardized templates for WARNING, CRITICAL, EVACUATION
├── alert_service.py             # SQLite database layer for alerts and delivery logs
├── channels/                    # Pluggable channel delivery drivers
│   ├── __init__.py
│   ├── base.py                  # BaseAlertChannel abstract protocol
│   ├── sms.py                   # SMS driver (Twilio / HTTP Gateway with simulation fallback)
│   ├── whatsapp.py              # WhatsApp driver (Meta Cloud API / Twilio with fallback)
│   └── telegram.py              # Telegram Bot driver (Bot API with simulation fallback)
├── models/                      # Pydantic schemas, requests, responses, and enums
│   ├── __init__.py
│   └── alert.py                 # AlertSeverity, TriggerType, ChannelType, DeliveryStatus
├── routes/                      # FastAPI HTTP endpoints
│   ├── __init__.py
│   └── alert_routes.py          # Router mounted at /api/alerts
└── utils/                       # Utility functions
    ├── __init__.py
    └── helpers.py               # Phone normalization, PII recipient masking, ALT-XXXX generator
```

---

## 3. Automated Trigger Conditions & Severity Tiers

The `alert_rules.py` module evaluates three primary hydrological/meteorological indicators:

| Trigger Factor | Evaluation Rule | Calculated Severity |
| :--- | :--- | :--- |
| **Risk Score Threshold** | `risk_score > 0.70` (70%) | `WARNING` (if ≤ 85%), `CRITICAL` (if > 85%), `EVACUATION` (if ≥ 95%) |
| **River Level Threshold** | `river_level >= 9.0m` (Critical Mark)<br>`river_level >= 8.0m` (Warning Mark) | `CRITICAL` / `EVACUATION`<br>`WARNING` |
| **Rainfall Forecast** | `rainfall_forecast >= 150.0mm` (24h) | `CRITICAL` (if ≥ 180mm: `EVACUATION`) |

When multiple triggers fire simultaneously (e.g. Risk Score 88% + River Level 9.2m + Rainfall 165mm), the system classifies the event as `TriggerType.MULTI_FACTOR` and escalates to the highest matching severity tier.

### Duplicate Alert Cooldown & Escalation Override

To prevent notification fatigue during continuous sensor polling:
- **Default Cooldown**: Identical alerts for the same catchment and severity tier are suppressed if triggered within a **15-minute cooldown window**.
- **Severity Escalation Override**: If incoming sensor telemetry escalates severity (`WARNING` $\rightarrow$ `CRITICAL` $\rightarrow$ `EVACUATION`), the cooldown is **immediately bypassed**, guaranteeing urgent life-safety warnings broadcast without delay.

---

## 4. Multi-Channel Templates

Emergency communications are formatted specifically for each channel's layout:

### SMS (Cellular Plain Text — Ultra-Concise)
```text
[PRAVAH ALERT] EVACUATION: Extreme flash flood hazard at Western Ghats - Pune/Lonavala. Inundation imminent. Move to designated high-ground shelters. Dial 112/1077.
```

### WhatsApp (Bold Rich Markdown with Indicators)
```text
🚨 *PRAVAH EMERGENCY FLOOD DISPATCH* 🚨
*Severity:* 🆘 *EVACUATION NOTICE*
*Catchment:* Western Ghats - Pune/Lonavala
*Trigger Factor:* Multi-factor hazard threshold exceeded (Risk 96%, River 9.8m, Rain 210mm)

⚠️ *Immediate Action Required:*
Water levels have breached critical flood marks. Low-lying river sectors are being inundated. Evacuate immediately along marked high-ground routes to designated relief shelters.

📍 *Emergency Route:* Follow bypass road away from riverbed
🏥 *Nearest Relief Camp:* Municipal Community Center / High School Grounds
📞 *NDRF / SDRF Hotline:* 112 / 1077
_PRAVAH Early Warning System • Automated Broadcast_
```

### Telegram (HTML Format for Emergency Channels)
```html
<b>🚨 PRAVAH EMERGENCY FLOOD DISPATCH</b>
<b>Severity:</b> 🆘 <code>EVACUATION</code>
<b>Target Sector:</b> <i>Western Ghats - Pune/Lonavala</i>
<b>Trigger Factor:</b> Multi-factor hazard threshold exceeded

<b>Operational Directives:</b>
Water levels have breached critical flood marks. Low-lying river sectors are being inundated. Evacuate immediately along marked high-ground routes.

• <b>Nearest Relief Camp:</b> Municipal Community Center
• <b>Emergency Helpline:</b> 112 / 1077
<a href="https://pravah.ndma.gov.in/shelters">View Designated Evacuation Routes & GIS Map</a>
```

---

## 5. Fault-Tolerant Concurrent Dispatch

Channel dispatch is coordinated via `asyncio.gather(..., return_exceptions=True)` in `AlertManager`:

```python
tasks = [
    self._dispatch_channel(channel_name, alert_record, recipient, rendered_messages[channel_name])
    for channel_name in channels
]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Key Resilience Guarantees**:
1. **Error Isolation**: If SMS telecom network fails or times out, WhatsApp and Telegram dispatches still complete successfully.
2. **Deterministic Audit Log**: Each channel attempt produces an independent row in `alert_channel_deliveries` recording message ID, HTTP provider response, latency, and error reason if failed.
3. **Partial Delivery Handling**: If at least one channel succeeds, the alert status is logged as `DELIVERED` or `PARTIAL`, ensuring responders have complete audit transparency.

---

## 6. REST API Reference

The router is mounted at `/api/alerts` in `src/api/app.py`:

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/alerts/trigger` | Evaluates triggers or manual dispatch; fires multi-channel notifications |
| `GET` | `/api/alerts` | Lists dispatched alerts with filtering by severity, channel, status, and query |
| `GET` | `/api/alerts/history` | Alias for alert history records |
| `GET` | `/api/alerts/stats` | KPI statistics (total, evacuation, critical, warning, delivery success rate) |
| `GET` | `/api/alerts/status` | Real-time connectivity and sandbox status for SMS, WhatsApp, and Telegram |
| `GET` | `/api/alerts/{id}` | Complete detail of a single alert including per-channel delivery records |
| `POST` | `/api/alerts/send` | **Legacy single-channel endpoint** (Twilio WhatsApp) preserved for backward compatibility |

### Sample Trigger Payload (`POST /api/alerts/trigger`)
```json
{
  "location": "Western Ghats — Pune / Lonavala Headwaters",
  "risk_score": 0.88,
  "river_level": 9.3,
  "rainfall_forecast": 165.0,
  "channels": ["sms", "whatsapp", "telegram"],
  "custom_notes": "Koyna Dam discharge increased to 45,000 cusecs."
}
```

---

## 7. Alerts Center Dashboard (`alerts.html`)

The command-center interface provides:
- **Channel Gateway Health Strip**: Real-time status cards for SMS, WhatsApp, and Telegram showing provider connection, mode (Live vs Sandbox Demo), and latency.
- **KPI Summary Cards**: Dispatched counts categorized by Evacuation (Tier 3), Critical (Tier 2), Warning (Tier 1), Deliveries Reliability %, and Active Cooldown timer.
- **Operations & Filter Toolbar**: Full-text search and filter pills for instant triage by severity and communication medium.
- **Audit Table**: Live tabular telemetry showing Alert Code (`ALT-XXXX`), Timestamp, Severity badge, Location, Trigger Reason, per-channel delivery indicators (`✓ Sent`, `✕ Err`, `⏳ Pend`), and an `Inspect` action.
- **Simulation & Trigger Modal**: Pre-configured with 3 one-click scenarios (`⚠️ Rising River Warning`, `🚨 Multi-Factor Critical Risk`, `🆘 Imminent Cloudburst Evacuation`) plus custom risk sliders and river gauge inputs for live demonstrations.
- **Inspection Drawer**: Deep inspection of raw payloads, recipient masking (`+91 ••••• ••890`), provider message IDs, and exact channel-rendered previews.

---

## 8. Configuration & Environment Variables

When production credentials are provided, live gateways are engaged automatically. When omitted, providers switch seamlessly into realistic **sandbox presentation mode** so demonstrations and tests never fail:

```env
# SMS Gateway (Twilio SMS or National Telecom HTTP Gateway)
SMS_PROVIDER_API_KEY="your-sms-api-key"
SMS_PROVIDER_URL="https://api.sms-gateway.com/v1/send"
SMS_SENDER_ID="PRAVAH"

# WhatsApp Gateway (Meta Cloud API or Twilio WhatsApp)
WHATSAPP_API_KEY="EAAB..."
WHATSAPP_PHONE_NUMBER_ID="1092837465"
# Or Twilio WhatsApp
TWILIO_ACCOUNT_SID="AC..."
TWILIO_AUTH_TOKEN="..."
TWILIO_WHATSAPP_NUMBER="whatsapp:+14155238886"

# Telegram Bot Gateway
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="-1001234567890"

# Cooldown Configuration
ALERT_COOLDOWN_MINUTES=15
```

---

## 9. Verification & Test Suite

The module is verified through automated test suites:
- **Unit & Integration Suite**: `tests/test_multichannel_alerts.py` (14/14 tests passing).
- **Full Project Regression**: `pytest` (74/74 tests passing).
- **Frontend Production Build**: `npm run build` completed with code 0.
