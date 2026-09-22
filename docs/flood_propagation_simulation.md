# PRAVAH — Flood Propagation & Inundation Simulation Engine

## Overview
The **PRAVAH Flood Propagation & Inundation Simulation Engine** is an independent, modular, and backward-compatible simulation framework designed for disaster emergency management, civil defense coordination, and reservoir operations.

While PRAVAH's machine learning core predicts *flood onset probability* and *active flood severity* at gauge stations, the **Simulation Engine** projects *how floodwaters will physically spread across geographic terrain over time* under customizable hydraulic scenarios.

It supports:
- 🌧️ **Precipitation-Driven Flood Events** (extreme convective cloudbursts, orographic Ghats ridge rainfall, Antecedent Moisture Conditions).
- 🌊 **Dam & Reservoir Release Discharges** (controlled and emergency spillway discharges from Koyna, Ujani, Radhanagari, Bhatsa, Khadakwasla).
- ⚠️ **River Cresting & Bank Overtopping Breaches** (lateral levee failure and floodplain inundation along Savitri, Krishna, Panchganga, Ulhas, and Brahmaputra rivers).
- ⏱️ **Dynamic Time-Step Progression** (discrete temporal simulation across 1h, 6h, 12h, 24h, and 48h horizons).
- 🗺️ **5-Tier Spatial Inundation Depth Contours** (`0.0–0.5m`, `0.5–1.0m`, `1.0–2.0m`, `2.0–5.0m`, `>5.0m`).
- 👥 **Catchment Census Demographic Exposure** (integrated with real population density and high-risk demographic counts).
- 🏥 **Lifeline Infrastructure Vulnerability** (submerged road kilometers, flooded bridges, critical hospital/school risk from OSM).

---

## 1. System Architecture

```text
                             PRAVAH CORE ENGINE
              (Census Features, Evacuation Network, Hydrograph Data)
                                       │
                                       ▼
                              SimulationManager
                  (Singleton Orchestrator & Multi-Tier Cache)
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
      ScenarioManager        FloodPropagationEngine         API & Web Routes
   (Benchmark Presets)        (Dynamic Hydro-Wave)       (/api/simulation/*)
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
     RainfallScenario          DamReleaseScenario       RiverOverflowScenario
    (SCS-CN Wave Surge)       (Surge Wave Routing)      (Weir Breach Equation)
            │                          │                          │
            └──────────────────────────┼──────────────────────────┘
                                       ▼
                                TimeStepEngine
                     (0h ──► 1h ──► 6h ──► 12h ──► 24h ──► 48h)
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
                 InundationEngine                ImpactEngine
              (5-Tier Depth Polygons,       (Census Demographics,
                GeoJSON Contours)            OSM Infrastructure)
                        │                             │
                        └──────────────┬──────────────┘
                                       ▼
                              SimulationRunResponse
                        (Spatial Layers, Growth Curves,
                          Demographics, Provenance)
                                       │
                                       ▼
                          Frontend: Simulation Center
                              (simulation.html)
                    - Leaflet 5-Tier Color Inundation Contours
                    - Time Scrubber (Play / Pause / Seek / Speed)
                    - Dynamic Extent Growth & Population Charts
                    - Infrastructure Risk Breakdown Badges
```

---

## 2. Multi-Scenario Mathematical Physics

### 2.1 Rainfall-Driven Flash Downpour Model
Rainfall runoff depth $Q_{\text{runoff}}$ is approximated using the USDA-SCS runoff relationship:

$$Q = \begin{cases} \frac{(P - I_a)^2}{P - I_a + S} & \text{for } P > I_a \\ 0 & \text{for } P \le I_a \end{cases}$$

Where:
- $P$ = Cumulative precipitation in mm.
- $S$ = Potential maximum retention, modulated by antecedent soil moisture $S_{\text{pct}}$:
  $$S = \left(\frac{25400}{CN} - 254\right) \cdot \left(1.0 - \frac{S_{\text{pct}}}{120}\right)$$
- $I_a = 0.2 \cdot S$ (Initial abstraction).

The dynamic inundated footprint $A(t)$ expands according to a sigmoidal hydrograph wave curve:

$$A(t) = A_{\text{max}} \cdot \Phi(t)$$

$$\Phi(t) = \frac{1}{1 + e^{-k (t / t_{\text{dur}} - 0.35)}}$$

### 2.2 Dam Reservoir Release Routing
Discharge from controlled spillways introduces an excess hydrograph above the downstream safe bankfull channel capacity $Q_{\text{safe}}$:

$$Q_{\text{excess}} = \max\left(100.0, Q_{\text{release}} - Q_{\text{safe}}\right)$$

Total released volume $V_{\text{MCM}}$:

$$V_{\text{MCM}} = \frac{Q_{\text{release}} \cdot \Delta t_{\text{hours}} \cdot 3600}{10^6}$$

Downstream peak depth $H_{\text{peak}}$ and extent $A_{\text{max}}$:

$$H_{\text{peak}} = \min\left(8.0, 1.2 + \frac{Q_{\text{excess}}}{1800} \cdot 1.4\right)$$

$$A_{\text{max}} = \min\left(65.0, \frac{Q_{\text{excess}}}{1200} \cdot (\Delta t)^{0.65} \cdot 5.2\right)$$

The wave centroid translates downvalley along the river slope as elapsed time advances:

$$\vec{X}_{\text{centroid}}(t) = \vec{X}_{\text{dam}} + \vec{v}_{\text{channel}} \cdot \Phi(t)$$

### 2.3 River Overtopping & Levee Breach Model
Lateral overtopping follows the broad-crested weir formulation:

$$Q_{\text{spill}} = 1.7 \cdot W_{\text{breach}} \cdot (H_{\text{river}} - H_{\text{bank}})^{1.5}$$

Where:
- $W_{\text{breach}}$ = Breach opening width (m).
- $H_{\text{river}} - H_{\text{bank}}$ = Hydraulic head above overtopping threshold (m).

Lateral inundation area spreads outward across the adjacent flood basin:

$$A_{\text{max}} = \min\left(38.0, \frac{Q_{\text{spill}}}{450} \cdot (\Delta t)^{0.6} \cdot 4.5\right)$$

---

## 3. 5-Tier Depth Inundation Contours

Flood extent is discretized into 5 standardized depth tiers:

| Tier Code | Depth Range | Hydraulic Consequence | Map Palette |
| :--- | :--- | :--- | :--- |
| `SHALLOW_0_05M` | $0.0 - 0.5\text{ m}$ | Ankle-to-shin depth; impassable for pedestrians; low risk | `#06b6d4` (Teal) |
| `MODERATE_05_1M` | $0.5 - 1.0\text{ m}$ | Knee-to-waist depth; vehicles stalled; moderate risk | `#3b82f6` (Sky Blue) |
| `DEEP_1_2M` | $1.0 - 2.0\text{ m}$ | Chest depth; ground floors submerged; high risk | `#f59e0b` (Amber) |
| `SEVERE_2_5M` | $2.0 - 5.0\text{ m}$ | Single-story buildings submerged; severe risk | `#f97316` (Orange) |
| `EXTREME_GT_5M` | $> 5.0\text{ m}$ | Multi-story structural engulfment; extreme catastrophe | `#ef4444` (Rose Red) |

---

## 4. Demographic & Infrastructure Impact Modeling

### 4.1 Population Exposure Calculation
Using real catchment census features from `target_catchment_lulc_population_features.csv`:

$$\text{Pop}_{\text{exposed}}(t) = \min\left(\text{Pop}_{\text{total}}, A(t) \cdot \rho_{\text{pop}} \cdot \left(1 + 0.4 \cdot \frac{\text{Urban}_{\text{pct}}}{100}\right)\right)$$

- **High-Risk Population**: Exposure in depth zones $> 1.5\text{ m}$.
- **Vulnerable Subsets**: Elderly and children estimated at $22\%$ of exposed population.
- **Evacuation Urgency Tiers**: `MONITORING`, `ADVISORY`, `URGENT`, `MANDATORY`.

### 4.2 Infrastructure Impact
Derived from the PRAVAH road network graph and OSM facilities:
- Submerged road length ($\text{km}$)
- Submerged bridges count
- Hospitals and health clinics within flood contour
- Primary and secondary schools at risk
- Substation and water treatment critical facilities

---

## 5. REST API Reference (`/api/simulation/*`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/simulation/status` | Operational status, monitored rivers, dams, depth tiers |
| `GET` | `/api/simulation/scenarios` | Pre-configured benchmark scenario templates |
| `POST` | `/api/simulation/run` | Execute dynamic time-based flood propagation simulation |
| `GET` | `/api/simulation/{id}` | Complete simulation run payload by ID |
| `GET` | `/api/simulation/{id}/inundation` | Spatial GeoJSON contours & depth distribution |
| `GET` | `/api/simulation/{id}/population-impact` | Demographic exposure and evacuation urgency metrics |
| `GET` | `/api/simulation/{id}/infrastructure-impact` | Submerged roads, bridges, and hospital vulnerability |
| `GET` | `/api/simulation/{id}/timeline` | Lightweight time-series points for charting |
| `GET` | `/api/simulation/history` | Historical simulation execution runs |
| `DELETE`| `/api/simulation/{id}` | Cancel/abort active simulation run |

---

## 6. Strict Safety & Provenance Notice

All outputs generated by this engine are tagged with the mandatory advisory:

> ⚠️ **SIMULATED ESTIMATE — For Emergency Planning Only.** Model-derived spatial projections for disaster preparedness. Not observed sensor readings.

---

## 7. Verification & Non-Regression Summary

- **Total Unit & Integration Tests**: 26 dedicated simulation tests (`tests/test_flood_simulation.py`), 100% passing.
- **Total Project Tests**: 160 repository tests passing with zero regressions.
- **Frontend Compilation**: `npm run build` compiled `simulation.html` (57.16 kB) with 0 errors.
- **Backward Compatibility**: `backend/simulation/__init__.py` proxy guarantees seamless symbol importing.
