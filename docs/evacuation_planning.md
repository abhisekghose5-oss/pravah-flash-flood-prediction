# PRAVAH — Evacuation Planning & Safe Route Generation Engine

## 1. Executive Summary & Architectural Overview

The **Evacuation Planning & Safe Route Generation Engine** is an independent, modular, production-grade routing system integrated into the PRAVAH flood early-warning platform. In disaster events—such as Western Ghats river valley cloudbursts or Brahmaputra flash floods—standard shortest-path navigation fails because primary roads may be submerged, bridges inundated, or designated shelters overburdened.

The PRAVAH Evacuation Engine continuously synthesizes:
1. **Dynamic Flood-Risk Zones**: Spatial polygons with telemetry-driven hazard scores (0.0 to 1.0) and safety tiers (`LOW`, `MODERATE`, `HIGH`, `EXTREME`).
2. **Real-Time Road Closures**: Live blockage reports and structural integrity advisories (`OPEN`, `PARTIALLY_BLOCKED`, `CLOSED`, `UNKNOWN`).
3. **Shelter Capacities & Status**: Relief camp capacities, live evacuee counts, intake eligibility, and accessibility.
4. **Topological Graph Network**: Multi-modal nodes, road segments, baseline speeds, and elevation heuristics.
5. **Intelligent Pathfinding Algorithms**: Priority-queue **Dijkstra** and admissible Haversine **A\*** strategies generating safety-scored routes across multiple evacuation objectives (`FASTEST`, `LOWEST_RISK`, `NEAREST_SHELTER`, `BALANCED`).

The module is strictly additive and backward-compatible. All existing single-hop evacuation endpoints (`GET /api/evacuation-route` and `GET /api/v1/evacuation/nearest`) remain 100% operational for existing integrations.

```text
               HYDROLOGICAL, TELEMETRY & SPATIAL INPUTS
    ┌───────────────────────┬───────────────────────┬───────────────────────┐
    │  Flood Risk Telemetry │   Road Closure Feeds  │ Shelter Capacity State│
    │  (FloodRiskService)   │  (RoadClosureService) │   (ShelterService)    │
    │  • 6 High-Risk Basins │  • Active Blockages   │  • 16 Active Shelters │
    │  • Dynamic Risk Scores│  • Segment Exclusion  │  • Capacity Check     │
    └───────────┬───────────┴───────────┬───────────┴───────────┬───────────┘
                │                       │                       │
                └───────────────────────┼───────────────────────┘
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                   RiskEngine Hazard Synchronization                     │
  │  • Maps Spatial Hazards to Road Segments                                │
  │  • Prunes/Disables Closed Road Edges from Graph                         │
  │  • Updates Effective Risk & Blockage Delay Constants                    │
  └─────────────────────────────────────┬───────────────────────────────────┘
                                        │
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │               EvacuationManager Central Orchestrator                    │
  │                                                                         │
  │  ┌───────────────────────┐   ┌───────────────────┐   ┌───────────────┐  │
  │  │ RoadNetwork Graph     │   │ RouteEngine       │   │ RouteScoring  │  │
  │  │ • 34+ Strategic Nodes │──>│ Strategy Pattern  │──>│ Cost Function │  │
  │  │ • Bi-directional Edges│   │ • Dijkstra / A*   │   │ Delays & Risk │  │
  │  └───────────────────────┘   └───────────────────┘   └───────┬───────┘  │
  │                                                              │          │
  │                      ┌───────────────────────────────────────┘          │
  │                      ▼                                                  │
  │    Multi-Objective Route Formulation:                                   │
  │    • FASTEST          (Minimizes Travel Time)                           │
  │    • LOWEST_RISK      (Heavily Penalizes Flood Exposure)                │
  │    • NEAREST_SHELTER  (Minimizes Distance to Available Shelter)         │
  │    • BALANCED         (Multi-Criteria Tradeoff)                         │
  │    Safety Classification: LOW RISK | MODERATE RISK | HIGH RISK | UNSAFE │
  └─────────────────────────────────────┬───────────────────────────────────┘
                                        │
                                        ▼
         ┌─────────────────────────────────────────────────┐
         │        SQLite Persistence & Audit Trail         │
         │          (data/pravah_telemetry.db)             │
         │  • Table: evacuation_routes                     │
         │  • Logs: Request, Path, Cost, Risk, & Rationale │
         └──────────────────────┬──────────────────────────┘
                                │
             ┌──────────────────┴──────────────────┐
             ▼                                     ▼
 ┌───────────────────────────────┐   ┌───────────────────────────────┐
 │ Evacuation Mission Dashboard  │   │ REST API Endpoints            │
 │ (`evacuation.html`)           │   │ Mounted under `/api/evacuation`│
 │ • Interactive Leaflet Map     │   │ • POST /route                 │
 │ • Real-Time Route Switching   │   │ • GET  /shelters              │
 │ • Shelter & Closure Overlays  │   │ • GET  /risk-zones            │
 │ • Turn-by-Turn Waypoints      │   │ • GET  /road-closures         │
 └───────────────────────────────┘   └───────────────────────────────┘
```

---

## 2. Directory Structure & Module Layout

All backend evacuation planning components reside under `src/evacuation/`:

```
src/evacuation/
├── __init__.py                  # Public package interface & exports
├── evacuation_config.py         # Routing weights, travel delays, speed baselines, safety tiers
├── road_network.py              # RoadNetwork graph structure & default node/edge seeding
├── route_scoring.py             # Edge cost evaluation, travel time computation, safety tiering
├── route_engine.py              # Strategy-pattern pathfinder (DijkstraStrategy, AStarStrategy)
├── risk_engine.py               # Spatial hazard overlay mapping to graph edges
├── evacuation_manager.py        # Central evacuation orchestrator & alternative route generator
├── algorithms/
│   ├── __init__.py              # Algorithm exports
│   ├── dijkstra.py              # Min-heap priority-queue Dijkstra implementation
│   └── astar.py                 # Admissible Haversine heuristic A* pathfinder
├── models/
│   ├── __init__.py              # Pydantic data model exports
│   ├── road.py                  # RoadSegment & RoadStatus enum
│   ├── shelter.py               # Shelter & ShelterStatus enum
│   ├── risk_zone.py             # RiskZone & RiskLevel enum
│   └── route.py                 # RouteRequest, EvacuationRoute, EvacuationPlanResponse
├── routes/
│   ├── __init__.py              # Router exports
│   └── evacuation_routes.py     # FastAPI router mounted at /api/evacuation
├── services/
│   ├── __init__.py              # Service layer exports
│   ├── shelter_service.py       # Shelter database sync & intake capacity management
│   ├── flood_risk_service.py    # Basin flood risk zone repository
│   ├── road_closure_service.py  # Road closure & blockage reporting
│   └── route_service.py         # SQLite route audit logging & history
└── utils/
    ├── __init__.py              # Geo-utility exports
    └── geo_utils.py             # Haversine distance, polyline length, point interpolation
```

---

## 3. Mathematical Formulation & Routing Cost Models

### 3.1 Dynamic Edge Cost Function

For an edge $e = (u, v)$ with road length $d$ (km), baseline vehicle speed $s$ (km/h), effective flood risk score $R \in [0.0, 1.0]$, road status $S \in \{\text{OPEN}, \text{PARTIALLY\_BLOCKED}, \text{CLOSED}\}$, and travel mode $M$:

If $S = \text{CLOSED}$, the edge cost is infinite ($\infty$), pruning it from the pathfinding search space.

For passable edges, the base travel time is:
$$T_{\text{base}} = \frac{d}{s} \times 60 \quad (\text{minutes})$$

Additional obstruction and flood risk delays are computed dynamically:
- **Obstruction Delay**: If $S = \text{PARTIALLY\_BLOCKED}$, $T_{\text{delay\_block}} = 15.0 \text{ mins}$ (vehicles) or $8.0 \text{ mins}$ (foot).
- **Hydrological Inflow Delay**: $T_{\text{delay\_flood}} = R \times 5.0 \text{ mins}$ (vehicles) or $R \times 12.0 \text{ mins}$ (foot).

The total effective travel time across edge $e$ is:
$$T_{\text{total}} = T_{\text{base}} + T_{\text{delay\_block}} + T_{\text{delay\_flood}}$$

### 3.2 Objective Optimization Formulations

Depending on the selected user objective, edge weights are computed as follows:

| Objective | Cost Optimization Formula | Design Intent |
| :--- | :--- | :--- |
| **`FASTEST`** | $C = T_{\text{total}}$ | Minimizes total transit duration to nearest available shelter. |
| **`LOWEST_RISK`** | $C = T_{\text{total}} \times 0.2 + (R \times 40.0 \times d) + (15.0 \text{ if blocked})$ | Heavily penalizes submerged and low-lying sectors, favoring elevated routes. |
| **`NEAREST_SHELTER`** | $C = d + (R \times 15.0 \times d)$ | Minimizes physical transit distance while preventing direct passage through critical flood hazards. |
| **`BALANCED`** | $C = 0.5 \times T_{\text{total}} + 0.3 \times (R \times 20.0 \times d) + 0.2 \times d$ | Multi-criteria optimization balancing evacuation time, safety margin, and fuel/stamina efficiency. |

### 3.3 A* Admissible Heuristic

For a current node $n$ and destination node $g$:
$$h(n, g) = \frac{\text{haversine}(n, g)}{s_{\max}} \times 60 \quad (\text{minutes})$$
where $s_{\max} = 90.0 \text{ km/h}$ is the maximum permissible network speed. Because Euclidean/Haversine distance is the physical lower bound on travel distance, $h(n, g) \le h^*(n, g)$, guaranteeing that the A* heuristic is strictly admissible and monotonically consistent.

### 3.4 Safety Classification Engine

Every generated evacuation plan is assigned a deterministic safety tier based on composite path metrics:

| Safety Tier | Threshold Criteria | Actionable Directive |
| :--- | :--- | :--- |
| **`LOW RISK`** | $\bar{R} < 0.25$ and $R_{\max} < 0.40$ | Safe for all civilian vehicles and pedestrian evacuation. |
| **`MODERATE RISK`** | $\bar{R} < 0.50$ and $R_{\max} < 0.70$ | Safe for four-wheel vehicles; high ground clearance recommended. |
| **`HIGH RISK`** | $\bar{R} < 0.75$ and $R_{\max} < 0.85$ | Emergency convoy / high-clearance rescue vehicles only. Proceed with extreme caution. |
| **`UNSAFE`** | $\bar{R} \ge 0.75$ or $R_{\max} \ge 0.85$ | Impassable for civilian transit; active water inflow across sector. |
| **`NO_SAFE_ROUTE_AVAILABLE`** | Search graph exhausted / all egress corridors blocked | Egress impossible. Seek immediate vertical shelter or signal for aerial rescue. |

---

## 4. Shelter Capacity & Dynamic Exclusion Logic

The PRAVAH shelter network maintains real-time intake telemetry across 16 pre-seeded relief centers:
- **Pune District**: Balewadi Sports Complex, Shivajinagar Govt College, Sinhagad Elevated Relief Camp, Pimpri Community Center.
- **Karad / Satara Basin**: Karad Municipal High School, Krishna Valley Polytechnic, Malkapur Community Center.
- **Mahad / Savitri Corridor**: Mahad Dr. Ambedkar College, Poladpur Govt Rest House.
- **Chiplun / Vashishti Corridor**: Chiplun DBJ College Campus, Guhagar Coastal Cyclone Shelter.
- **Kolhapur Catchment**: Kolhapur Shivaji University Gymkhana, Rajaram College Relief Center.
- **Guwahati / Brahmaputra**: Sarusajai Sports Complex, Cotton University Relief Wing, Jalukbari Higher Secondary Shelter.

### Dynamic Bypass Rules
1. If $\text{status} = \text{FULL}$ or $\text{occupancy} \ge \text{capacity}$, the shelter is excluded from candidate destination selection.
2. If $\text{status} = \text{CLOSED}$, the shelter is pruned.
3. The engine dynamically redirects evacuees to the next closest shelter with verified available capacity.

---

## 5. REST API Reference (`/api/evacuation`)

### 5.1 Generate Evacuation Plan
- **Method & Endpoint**: `POST /api/evacuation/route`
- **Request Body**:
```json
{
  "start_lat": 18.5204,
  "start_lon": 73.8567,
  "destination_shelter_id": null,
  "objective": "FASTEST",
  "travel_mode": "DRIVING",
  "algorithm": "DIJKSTRA",
  "avoid_closures": true,
  "max_acceptable_risk": 0.85
}
```
- **Response Format**:
```json
{
  "request_id": "req-a7b3c2d1e0",
  "primary_route": {
    "route_id": "rte-5f9a2b",
    "objective": "FASTEST",
    "algorithm_used": "DIJKSTRA",
    "total_distance_km": 4.82,
    "total_duration_mins": 11.5,
    "average_risk_score": 0.12,
    "max_risk_score": 0.20,
    "safety_classification": "LOW RISK",
    "destination_shelter": {
      "shelter_id": "shelter-pune-02",
      "name": "Shivajinagar Govt College Evacuation Camp",
      "capacity": 800,
      "current_occupancy": 320,
      "status": "AVAILABLE"
    },
    "waypoints": [ ... ],
    "polyline_coords": [ [18.5204, 73.8567], ... ],
    "hazards_encountered": [],
    "closed_roads_avoided": 0,
    "delay_mins": 0.0
  },
  "alternative_routes": [ ... ],
  "status_code": "SUCCESS",
  "message": "Safe evacuation route computed successfully."
}
```

### 5.2 Shelter Management
- `GET /api/evacuation/shelters`: List all relief shelters with capacity and coordinates. Supports query parameters `basin` and `available_only=true`.
- `GET /api/evacuation/shelters/{id}`: Detailed metadata for a specific shelter.
- `POST /api/evacuation/shelters`: Register a new emergency relief camp.
- `PATCH /api/evacuation/shelters/{id}`: Update shelter capacity, occupancy, and operational status.

### 5.3 Hazard & Infrastructure Telemetry
- `GET /api/evacuation/risk-zones`: Active spatial flood risk zones with severity scores.
- `POST /api/evacuation/risk-zones`: Register or update dynamic flood hazard zones.
- `GET /api/evacuation/road-closures`: Current road blockages and closures.
- `POST /api/evacuation/road-closures`: Report new road obstruction or water inundation.
- `DELETE /api/evacuation/road-closures/{id}`: Clear road closure upon water recession.

### 5.4 Historical Route Inquiries
- `GET /api/evacuation/routes`: Paginated history of generated evacuation routes.
- `GET /api/evacuation/routes/{id}`: Full waypoint and safety trace of a past route.
- `GET /api/evacuation/network`: Network graph telemetry (node count, edge count, active closures).

---

## 6. Frontend Mission Dashboard (`evacuation.html`)

The standalone command center provides an emergency GIS interface:
- **Interactive CartoDB Dark Matter Map**: High-contrast, clean emergency mapping.
- **Live Overlays**:
  - **Relief Shelters**: Neon green (Available) and red (Full/Closed) pulsed markers with real-time occupancy meters.
  - **Road Closures**: Bright red dashed polyline segments displaying closure reasons and detour advisories.
  - **Flood Risk Zones**: Semi-transparent amber/red circular catchment polygons.
  - **Active Route Polylines**: Glowing neon blue/emerald polylines with directional arrows and turn-by-turn waypoints.
- **Interactive Tactical Sidebar**:
  - **GPS Locate Me**: One-click geolocation acquisition.
  - **Catchment Presets**: Instant fly-to buttons for Pune, Karad, Mahad, Chiplun, Kolhapur, and Guwahati.
  - **Routing Objective Selectors**: Toggle between Fastest, Lowest Risk, Nearest Shelter, and Balanced routes.
  - **Alternative Route Cards**: Visual cards displaying distance, estimated transit time, and risk level with click-to-preview polyline switching.
  - **Turn-by-Turn Navigation Queue**: Step-by-step waypoint directions with elevation and risk indicators.
