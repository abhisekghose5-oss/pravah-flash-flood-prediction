# PRAVAH — Digital Twin Studio & Hydrological Simulation Module

## Overview
The **PRAVAH Digital Twin Studio** is an independent, modular geospatial simulation platform that provides a virtual representation of monitored river basins and watersheds across the **Maharashtra Western Ghats** (Krishna, Savitri, Vashishti, Panchganga, Ulhas, Godavari) and **Northeast India** (Brahmaputra, Beki, Dhansiri).

It empowers flood operators, hydrologists, and emergency managers to simulate how rainfall translates into surface runoff, downhill channel routing, and localized water accumulation before catastrophic flood peaks occur.

---

## 1. System Architecture

```text
                               PRAVAH DATASETS
                  (target_catchments.geojson, characteristics.csv,
                   northeast_candidate_catchments.geojson, DEM)
                                      │
                                      ▼
                             DigitalTwinManager
                         (Central Orchestration)
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
      WatershedModel             TerrainModel            RiverBasinModel
    (Catchment Bounds,        (DEM Grid, Slope,         (Stream Channels,
     Drainage Areas)           Aspect, Gradients)        Strahler Orders)
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      ▼
                         HydrologicalSimulationEngine
                                      │
                ┌─────────────────────┴─────────────────────┐
                ▼                                           ▼
           RunoffModel                             AccumulationModel
         (SCS-CN Runoff,                          (Topological Routing,
       Infiltration, Peak Q)                       Depression Zones)
                │                                           │
                └─────────────────────┬─────────────────────┘
                                      ▼
                               SimulationOutput
                      (Runoff Layers, Accumulation Heatmap,
                        Water Flow Particle Vectors)
                                      │
                                      ▼
                        FastAPI (/api/digital-twin/*)
                                      │
                                      ▼
                      Frontend: Digital Twin Studio
                           (digital_twin.html)
                   - Interactive Leaflet Multi-Layer Map
                   - Timeline Controls (Play/Pause/Seek)
                   - Animated Particle Flow Vectors
                   - Real-Time Hydrological Results Panel
```

---

## 2. Mathematical Formulations & Hydrological Physics

### 2.1 SCS Curve Number (SCS-CN) Runoff Model
The engine computes surface runoff depth using the USDA Soil Conservation Service (SCS) Curve Number method, calibrated against catchment soil type and land cover:

1. **Antecedent Moisture Condition (AMC) Adjustment**:
   - $\text{AMC I}$ (Dry antecedent condition):
     $$CN_I = \frac{CN_{II}}{2.281 - 0.01281 \cdot CN_{II}}$$
   - $\text{AMC II}$ (Normal seasonal condition):
     $$CN_{II} = \text{Base Catchment Curve Number}$$
   - $\text{AMC III}$ (Saturated antecedent condition):
     $$CN_{III} = \frac{CN_{II}}{0.427 + 0.00573 \cdot CN_{II}}$$

2. **Potential Maximum Retention ($S$)**:
   $$S = \frac{25400}{CN} - 254 \quad (\text{mm})$$

3. **Initial Abstraction ($I_a$)**:
   $$I_a = 0.2 \cdot S \quad (\text{mm})$$

4. **Direct Runoff Depth ($Q$)**:
   $$Q = \begin{cases} \frac{(P - I_a)^2}{P - I_a + S}, & \text{if } P > I_a \\ 0, & \text{if } P \le I_a \end{cases} \quad (\text{mm})$$

5. **Volumetric Runoff ($V$)**:
   $$V = Q \times 10^{-3} \times (\text{Area in } km^2 \times 10^6) \quad (m^3)$$
   $$V_{\text{MCM}} = \frac{V}{10^6} \quad (\text{Million } m^3)$$

6. **Hydrograph Peak Discharge ($Q_p$)**:
   Using the SCS dimensionless unit hydrograph peak formula:
   $$T_p = 0.5 \cdot D + 0.6 \cdot T_c \quad (\text{hours})$$
   $$Q_p = \frac{0.208 \cdot \text{Area} \cdot Q}{T_p} \quad (m^3/s)$$

---

## 3. Water Accumulation & Classification

Topological water movement directs runoff from steep ridges down to lower-order stream channels and into natural depressions and riparian floodplains. Water accumulation is classified into 4 standardized severity zones:

| Severity Zone | Ponding Depth ($m$) | Typical Morphology | Emergency Advisory |
| :--- | :--- | :--- | :--- |
| **LOW** | $< 0.5\text{ m}$ | Upper valley terraces, gentle slopes | Routine drainage monitoring |
| **MODERATE** | $0.5\text{ m} - 1.5\text{ m}$ | Lowland fields, secondary tributaries | Alert local flood wardens |
| **HIGH** | $1.5\text{ m} - 3.0\text{ m}$ | Active riverbanks, confluence depressions | Initiate localized evacuation warnings |
| **EXTREME** | $> 3.0\text{ m}$ | Primary river channels, constricted gorges | Immediate mandatory evacuation |

---

## 4. REST API Reference

Mounted under `/api/digital-twin/`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/digital-twin/status` | System health, supported regions, and engine capabilities |
| `GET` | `/api/digital-twin/watersheds` | Full catalog of 66 monitored catchments with GeoJSON boundaries |
| `GET` | `/api/digital-twin/watersheds/{id}` | Detailed watershed metadata, drainage area, relief, sub-catchments |
| `GET` | `/api/digital-twin/terrain?watershed_id={id}` | Elevation contours, slope gradients, aspect azimuth, and hypsometry |
| `GET` | `/api/digital-twin/river-basins` | Aggregated river basin summaries and active station counts |
| `GET` | `/api/digital-twin/river-basins/{id}/network` | GeoJSON LineString stream network with Strahler orders |
| `GET` | `/api/digital-twin/scenarios` | Pre-configured benchmark scenarios (e.g. Mahad Cloudburst, Kolhapur 2019) |
| `GET` | `/api/digital-twin/layers` | Visual layer manifest and default toggles |
| `POST` | `/api/digital-twin/simulate` | Executes coupled physical runoff and water accumulation simulation |
| `GET` | `/api/digital-twin/runoff` | Lightweight parameter exploration for SCS-CN calculations |
| `GET` | `/api/digital-twin/accumulation` | Inundation footprint and depth ranges for given precipitation |

---

## 5. Digital Twin Studio Frontend

The studio frontend portal is accessible at `digital_twin.html` and offers:
- **Interactive Multi-Layer Map**: Independent layer toggling for Watershed Boundaries, Terrain Elevation, River Basin, Runoff Flow Paths, Water Accumulation, and Gauge Stations.
- **Simulation Timeline**: Play, Pause, Reset, and Seek scrubbers ($0\text{h} \to 24\text{h}$) with dynamic animated particle vectors traversing stream reaches.
- **Scenario Presets**: 1-click loading of historic benchmarks (e.g. Mahad Savitri Flash Flood, Panchganga 2019 Monsoon).
- **Physical Telemetry Panel**: Runoff depth, volumetric discharge ($Mm^3$), peak discharge ($m^3/s$), time to peak ($hrs$), and high accumulation footprint ($km^2$).
- **Disambiguation Badging**: Clear `SIMULATED ESTIMATE` pill to ensure no confusion with real-time measured gauge levels.
