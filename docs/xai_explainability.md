# PRAVAH — Explainable AI (XAI) Integration Module

## 1. Executive Summary & Architectural Overview

The **Explainable AI (XAI) Integration Module** delivers a transparent, production-ready interpretability layer for the PRAVAH flash-flood early-warning platform. While machine-learning models (such as deep ensembles or gradient boosted trees) achieve high predictive sensitivity, black-box predictions lack the interpretability required by emergency responders, district disaster management authorities (DDMAs), and central water commission engineers.

The PRAVAH XAI Engine bridges this gap by computing exact Shapley additive explanations (**SHAP**) across all deployed flood prediction models:
1. **Random Forest Classifier**: Bagging ensemble (300 estimators) operating in probability space.
2. **XGBoost Classifier**: Gradient-boosted trees operating on log-odds margins.
3. **LightGBM Classifier**: Histogram-based gradient boosted decision trees with leaf-wise splitting.

The module is strictly additive and non-intrusive. The existing flood inference pipeline (`POST /api/v1/predict/live`, `PravahInferenceEngine.predict_live()`) remains 100% untouched.

```text
                  PRAVAH INPUT (Gauge ID / 10-day Rainfall / Features)
                                         │
                                         ▼
                             EXISTING PREPROCESSING
                               (ColumnTransformer)
                                         │
                                         ▼
                                 EXISTING ML MODEL
                       (Random Forest / XGBoost / LightGBM)
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
                 ▼                                               ▼
          EXISTING OUTPUT                              OPTIONAL XAI MODULE
      (PravahInferenceEngine)                               (XAIManager)
                 │                                               │
                 │                               ┌───────────────┼───────────────┐
                 │                               ▼               ▼               ▼
                 │                          RandomForest      XGBoost         LightGBM
                 │                           Explainer       Explainer       Explainer
                 │                               │               │               │
                 │                               └───────────────┼───────────────┘
                 │                                               ▼
                 │                                    SHAP TreeExplainer Engine
                 │                                               │
                 │                               ┌───────────────┼───────────────┐
                 │                               ▼               ▼               ▼
                 │                         Local XAI       Global XAI      Visualizations
                 │                         • Why High/     • Summary Plot  • Force Plot
                 │                           Low Risk?     • Feature       • Directional
                 │                         • Normalized      Importance      Gauges
                 │                           Impact %      • Beeswarm
                 │                               │               │               │
                 │                               └───────────────┼───────────────┘
                 │                                               ▼
                 │                                   FeatureMapper Domain Layer
                 │                                   (Friendly Labels & Units)
                 │                                               │
                 ▼                                               ▼
     ┌───────────────────────┐                       ┌───────────────────────┐
     │ Existing PRAVAH UI &  │                       │ Standalone XAI Center │
     │ GIS Dashboard         │                       │ (`xai.html` & React)  │
     └───────────────────────┘                       └───────────────────────┘
```

---

## 2. Directory Structure & Module Layout

All backend explainability components reside under `src/xai/` (with a proxy re-export layer under `backend/xai/`):

```
src/xai/
├── __init__.py                  # Public package interface & exports
├── xai_manager.py               # Central singleton orchestrator & failure boundary
├── explainer_factory.py         # Thread-safe TreeExplainer caching & instantiation
├── explanation_service.py       # Data orchestration, preprocessing integration, background cache
├── feature_mapper.py            # Feature name sanitation, physical units, domain groups, narratives
├── shap_utils.py                # Contribution normalization, direction tagging, force plot builder
├── explainers/
│   ├── __init__.py              # Explainer exports
│   ├── base_explainer.py        # Abstract base class for model explainers
│   ├── random_forest_explainer.py # TreeExplainer for RandomForestClassifier
│   ├── xgboost_explainer.py     # TreeExplainer for XGBClassifier
│   └── lightgbm_explainer.py    # TreeExplainer for LGBMClassifier
├── models/
│   ├── __init__.py              # Pydantic schemas export
│   └── explanation.py           # ExplanationRequest, ExplanationResponse, ForcePlotData, etc.
├── routes/
│   ├── __init__.py              # Router export
│   └── xai_routes.py            # FastAPI router mounted under /api/xai
└── utils/
    ├── __init__.py              # Visualizer export
    └── visualization.py         # Responsive SVG formatters for Force Plot and Feature Importance
```

---

## 3. Mathematical Foundations & Shapley Attribution

### 3.1 Local Additive Feature Attribution

For a model $f(x)$ producing a prediction for input observation $x$, the SHAP framework defines an additive feature attribution model $g(z')$:
$$g(z') = \phi_0 + \sum_{i=1}^M \phi_i z_i'$$
where:
- $\phi_0 = \mathbb{E}[f(z)]$ is the baseline expected model output across the training distribution.
- $\phi_i \in \mathbb{R}$ is the Shapley attribution value for feature $i$.
- $z' \in \{0, 1\}^M$ is a binary coalition vector indicating feature presence.
- $M$ is the number of input features ($M = 109$ after `ColumnTransformer` preprocessing).

### 3.2 Normalized Relative Contribution

Because raw Shapley values can be expressed in log-odds margins (XGBoost) or probability offsets (Random Forest), reporting raw decimal values as civilian percentages can mislead operators. The PRAVAH engine computes normalized relative contribution percentages:
$$\text{RelContrib}_i = \frac{|\phi_i|}{\sum_{j=1}^M |\phi_j|} \times 100 \quad (\%)$$

This satisfies:
$$\sum_{i=1}^M \text{RelContrib}_i = 100\%$$
allowing operators to immediately identify the percentage share of model reasoning attributed to rainfall vs river stage vs topography.

### 3.3 Contribution Directionality

For each feature $i$:
$$\text{Direction}_i = \begin{cases} \text{increases\_risk} & \text{if } \phi_i > 0 \\ \text{decreases\_risk} & \text{if } \phi_i \le 0 \end{cases}$$

---

## 4. "Why High Risk?" vs "Why Low Risk?" Dynamic Synthesizer

The system dynamically adapts its headline narrative according to the predicted probability $\hat{y}$ and calibrated decision threshold $\tau$:

| Risk Tier | Condition | Headline Title | Dynamic Narrative Focus |
| :--- | :--- | :--- | :--- |
| **`EMERGENCY` / `WARNING`** | $\hat{y} \ge \tau$ | **WHY HIGH RISK?** | Highlights the top positive drivers (e.g. 24h cloudburst precipitation, elevated river stage, steep topography) driving probability past the critical threshold. |
| **`ADVISORY`** | $0.5\tau \le \hat{y} < \tau$ | **WHY MODERATE RISK?** | Highlights balanced tension: upward pressure from moderate inflow countered by available channel storage capacity. |
| **`NORMAL`** | $\hat{y} < 0.5\tau$ | **WHY LOW RISK?** | Highlights primary risk-suppressing factors (subdued antecedent rainfall, safe river stage margins, high soil infiltration). |

---

## 5. REST API Reference (`/api/xai`)

### 5.1 Explain Individual Prediction
- **Method & Path**: `POST /api/xai/explain`
- **Request Body**:
```json
{
  "gauge_id": "684",
  "rainfall_history_10d": [0.0, 5.0, 15.0, 30.0, 55.0, 80.0, 110.0, 45.0, 20.0, 65.0],
  "model_name": "RandomForest",
  "task": "onset"
}
```
- **Response**:
```json
{
  "status": "success",
  "model_used": "task_a_onset_RandomForest",
  "task": "onset",
  "station_name": "Karad",
  "prediction_probability": 0.1635,
  "decision_threshold": 0.2935,
  "risk_level": "ADVISORY",
  "headline_title": "WHY MODERATE RISK?",
  "headline_narrative": "Catchment exhibits moderate hydrological sensitivity (16.4%)...",
  "base_value": 0.500,
  "top_contributing_factors": [ ... ],
  "top_reducing_factors": [ ... ],
  "all_contributions": [ ... ],
  "force_plot": { ... },
  "disclaimer": "XAI explanations show which model inputs contributed to the prediction. They should not be interpreted as proof of direct causation."
}
```

### 5.2 Global Feature Importance
- **Method & Path**: `GET /api/xai/feature-importance?model=XGBoost&task=onset`
- **Response**: Ranked list of features by mean absolute SHAP attribution across diverse catchment profiles.

### 5.3 Global SHAP Summary
- **Method & Path**: `GET /api/xai/summary?model=LightGBM&task=onset`
- **Response**: Distribution points, impact directionality, and sample feature values for beeswarm plotting.

### 5.4 Standalone Force Plot
- **Method & Path**: `POST /api/xai/force-plot`
- **Response**: Base value, positive force total, negative force total, top directional features, and pre-rendered inline SVG markup.

### 5.5 Supported Models
- **Method & Path**: `GET /api/xai/models`
- **Response**: Catalog of operational models (`RandomForest`, `XGBoost`, `LightGBM`) and explainer readiness.

---

## 6. Frontend Mission Center (`xai.html`)

The standalone command center provides an interactive interface:
- **Model Selector Pill**: Switch seamlessly between Random Forest, XGBoost, and LightGBM.
- **Station / Catchment Dropdown**: Test real Western Ghats gauges (Karad, Mahad, Chiplun, Kolhapur, Pune) and Northeast stations (Beki).
- **Storm Presets**: One-click simulation of Cloudburst (180mm), Moderate (65mm), and Dry (5mm) events.
- **Dynamic "Why High/Low Risk?" Card**: Natural language breakdown with percentage contribution pills.
- **Interactive Force Plot**: Embedded SVG visualizing baseline $\rightarrow$ directional forces $\rightarrow$ predicted probability.
- **Global Feature Importance Bar Chart**: Ranked horizontal bars showing top 10 model drivers.
- **SHAP Summary Swarm**: Multi-feature distribution showing sensitivity to high vs low values.
- **Searchable Inventory Table**: Sort and inspect all 109 feature contributions.
- **Inspect Raw JSON Modal**: Instant payload verification for developers and evaluators.

---

## 7. Failure Isolation & Causal Limitations

### 7.1 Fault Isolation Guarantee
If `shap.TreeExplainer` throws an internal exception (due to numerical instability, unsupported custom feature keys, or memory limits), `XAIManager` catches the error, logs a trace, and returns an informative fallback response (`status = "error"`, `headline_title = "EXPLANATION TEMPORARILY UNAVAILABLE"`). **The primary prediction workflow continues to operate without interruption.**

### 7.2 Causal Boundary Notice
Shapley values represent mathematical feature attribution within the trained model's decision manifold; they **do not prove physical causation**. In empirical hydrology, high correlation between upstream rain and downstream flood stage is physically grounded, but model-based attributions should always be validated alongside physical gauge readings.
