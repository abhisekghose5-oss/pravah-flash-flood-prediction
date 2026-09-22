# PRAVAH — Production Deployment & Operational Guide

**System Version:** 2.5.0  
**Stack:** FastAPI (Python 3.10+), React / Vite (Node 18+), SQLite 3, Tailwind CSS, WebGL Mapbox/DeckGL

---

## 1. System Requirements

### Hardware Prerequisites
* **CPU:** 4+ Cores (recommended for SHAP TreeExplainer & hydraulic simulation)
* **RAM:** 8 GB minimum (16 GB recommended)
* **Storage:** 10 GB SSD storage space
* **OS:** Linux (Ubuntu 22.04 LTS / Debian 12) or Windows 10/11 Server

### Software Prerequisites
* Python 3.10 or higher
* Node.js v18.x or v20.x + npm
* SQLite 3.35+ (with JSON support)
* Git

---

## 2. Environment Configuration

Copy the sample environment file or update `.env` in the repository root:

```ini
# =============================================================================
# PRAVAH Production Environment Configuration
# =============================================================================

# Server Binding
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
LOG_LEVEL=INFO

# Telecom & Multi-Channel Alerting Providers
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567
TWILIO_WHATSAPP_NUMBER=+14155238886

# IVRS Voice Calling Engine
TWILIO_IVRS_PHONE_NUMBER=+15551234567
IVRS_VOICE_GENDER=alice
IVRS_VOICE_LANGUAGE=en-IN

# Telegram Community Broadcast Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_DEFAULT_CHAT_ID=-1001234567890

# Persistence & Data Paths
DATABASE_PATH=data/pravah_telemetry.db
DATA_UPLOAD_DIR=data/uploads
MODELS_DIR=models
```

> [!NOTE]
> If any of the above external provider tokens (`TWILIO_*`, `TELEGRAM_*`) are omitted, PRAVAH automatically operates in **Safe Sandbox Mode**. Notifications are generated, formatted, validated, and logged to SQLite without incurring telephony costs or throwing network errors.

---

## 3. Step-by-Step Deployment Procedure

### Step 1: Clone and Prepare Virtual Environment
```bash
git clone https://github.com/abhisekghose5-oss/pravah-flash-flood-prediction.git
cd pravah-flash-flood-prediction

python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Initialize Database & Run Migrations
```bash
python -m src.data.migrations
```
*Confirms that all schema entities (001 and 002) are verified and up to date.*

### Step 3: Build WebGL & Frontend Assets
```bash
npm install
npm run build
```
*Builds production bundles into the `dist/` directory.*

### Step 4: Launch FastAPI Production Server
For production Linux servers, use Uvicorn with Gunicorn worker management:
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
```
Or with Systemd Service (`/etc/systemd/system/pravah.service`):
```ini
[Unit]
Description=PRAVAH Flash-Flood Early Warning API
After=network.target

[Service]
User=pravah
WorkingDirectory=/opt/pravah-flash-flood-prediction
ExecStart=/opt/pravah-flash-flood-prediction/venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 4. Verification & Health Monitoring

Verify API readiness with `curl`:

```bash
# 1. Baseline System Health
curl -s http://localhost:8000/api/health | jq .

# 2. Unified 9-Subsystem Health
curl -s http://localhost:8000/api/integration/health | jq .

# 3. River Gauge Listing
curl -s http://localhost:8000/api/gauges?region=Maharashtra | jq .[0]
```
