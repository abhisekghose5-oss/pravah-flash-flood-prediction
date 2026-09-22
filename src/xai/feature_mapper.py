from __future__ import annotations

import re
from typing import Any, Dict, Tuple


# Known feature dictionaries: mapping clean key to (Friendly Name, Unit, Category)
FEATURE_METADATA_MAP: Dict[str, Tuple[str, str, str]] = {
    # Antecedent Precipitation
    "rain_1d": ("24-Hour Rainfall", "mm", "precipitation"),
    "rain_2d_sum": ("2-Day Cumulative Rainfall", "mm", "precipitation"),
    "rain_3d_sum": ("3-Day Cumulative Rainfall", "mm", "precipitation"),
    "rain_5d_sum": ("5-Day Cumulative Rainfall", "mm", "precipitation"),
    "rain_7d_sum": ("7-Day Cumulative Rainfall", "mm", "precipitation"),
    "rain_10d_sum": ("10-Day Cumulative Rainfall", "mm", "precipitation"),
    "rain_3d_max": ("3-Day Peak Daily Rainfall", "mm", "precipitation"),
    "rain_7d_max": ("7-Day Peak Daily Rainfall", "mm", "precipitation"),
    "rain_dry_days_3d": ("Dry Days in Last 72h", "days", "precipitation"),
    "has_gpm_coverage": ("GPM Satellite Radar Coverage", "flag", "precipitation"),
    # Hydrology & River Stage
    "Warning_Level": ("River Warning Threshold", "m", "hydrology"),
    "Danger_Level": ("River Danger Threshold", "m", "hydrology"),
    "Stream Order": ("Strahler River Stream Order", "order", "hydrology"),
    "Mainstem_Length": ("River Mainstem Length", "km", "hydrology"),
    "Basin_Area": ("Catchment Basin Area", "km²", "hydrology"),
    "Drainage_Density": ("Drainage Network Density", "km/km²", "hydrology"),
    "mean_annual_runoff": ("Mean Annual Surface Runoff", "mm/yr", "hydrology"),
    # Catchment Topography & Soil
    "Elevation": ("Catchment Elevation (DEM)", "m", "topography"),
    "Slope": ("Riparian Terrain Slope", "°", "topography"),
    "soil_moisture": ("Soil Moisture Saturation", "%", "topography"),
    "soil_depth": ("Subsurface Soil Depth", "cm", "topography"),
    "impervious_surface": ("Impervious Urban Surface", "%", "topography"),
    "vegetation_index": ("Vegetation Canopy Index (NDVI)", "index", "topography"),
    # Geospatial & Geographic
    "Latitude": ("Gauge Latitude", "°N", "geospatial"),
    "Longitude": ("Gauge Longitude", "°E", "geospatial"),
    "State": ("Administrative State", "text", "geospatial"),
    "Privacy": ("CWC Gauge Privacy Classification", "status", "geospatial"),
    "Basin": ("River Basin Identification", "text", "geospatial"),
    "River_Name": ("Monitored River System", "text", "hydrology"),
    "Station": ("Hydrological Gauge Station", "text", "geospatial"),
}


class FeatureMapper:
    """
    Translates raw and transformer-preprocessed technical model feature keys into
    human-readable names, physical engineering units, and domain categories.
    """

    @staticmethod
    def clean_key(raw_key: str) -> str:
        """Strip scikit-learn ColumnTransformer prefixes such as 'num__' or 'cat__'."""
        k = str(raw_key).strip()
        if k.startswith("num__"):
            k = k[5:]
        elif k.startswith("cat__"):
            k = k[5:]
        return k

    @classmethod
    def get_metadata(cls, raw_key: str) -> Tuple[str, str, str]:
        """
        Return (friendly_name, unit, domain_category) for any given feature key.
        """
        clean = cls.clean_key(raw_key)

        # 1. Exact match in catalog
        if clean in FEATURE_METADATA_MAP:
            return FEATURE_METADATA_MAP[clean]

        # 2. Check for One-Hot Encoded categorical naming: e.g. State_Maharashtra -> State: Maharashtra
        if "_" in clean:
            prefix, _, suffix = clean.partition("_")
            if prefix in FEATURE_METADATA_MAP:
                base_name, unit, cat = FEATURE_METADATA_MAP[prefix]
                return f"{base_name} ({suffix})", unit, cat

        # 3. Heuristic matching based on substring patterns
        lower = clean.lower()
        if "rain" in lower or "precip" in lower:
            label = clean.replace("_", " ").title()
            return label, "mm", "precipitation"
        if "level" in lower or "water" in lower or "stage" in lower or "river" in lower:
            label = clean.replace("_", " ").title()
            return label, "m", "hydrology"
        if "slope" in lower:
            return "Terrain Slope", "°", "topography"
        if "elev" in lower or "dem" in lower:
            return "Elevation", "m", "topography"
        if "soil" in lower or "sand" in lower or "clay" in lower:
            label = clean.replace("_", " ").title()
            return label, "%", "topography"
        if "area" in lower:
            label = clean.replace("_", " ").title()
            return label, "km²", "hydrology"

        # 4. Fallback: Title case formatting
        friendly = clean.replace("_", " ").title()
        return friendly, "", "other"

    @classmethod
    def generate_human_explanation(
        cls, feature_name: str, value: Any, shap_value: float, direction: str, unit: str
    ) -> str:
        """
        Produce a concise, contextual explanation explaining why this feature
        increased or decreased the model's flood risk prediction.
        """
        val_str = f"{value:.2f}" if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)
        unit_str = f" {unit}" if unit and unit not in ("flag", "status", "text", "order", "index") else ""

        if direction == "increases_risk":
            if "Rain" in feature_name or "Precip" in feature_name:
                return f"Substantial antecedent precipitation ({val_str}{unit_str}) actively saturated the upper catchment and accelerated runoff."
            elif "Warning" in feature_name or "Danger" in feature_name or "Water" in feature_name or "Level" in feature_name:
                return f"Elevated baseline river stage ({val_str}{unit_str}) reduces riparian capacity, elevating flash-flood onset probability."
            elif "Slope" in feature_name:
                return f"Steep catchment gradient ({val_str}{unit_str}) promotes rapid hydrograph concentration into low-lying floodplains."
            elif "Elevation" in feature_name:
                return f"Low elevation valley positioning ({val_str}{unit_str}) leaves this sector vulnerable to upstream water convergence."
            else:
                return f"{feature_name} observed at {val_str}{unit_str} exerted an upward push (+{abs(shap_value):.3f} SHAP) on flood probability."
        else:
            if "Rain" in feature_name or "Precip" in feature_name:
                return f"Subdued rainfall ({val_str}{unit_str}) prevented saturated overland flow, keeping flood risk suppressed."
            elif "Warning" in feature_name or "Danger" in feature_name:
                return f"Safe margins relative to danger benchmarks ({val_str}{unit_str}) indicate stable river channel flow."
            elif "Slope" in feature_name:
                return f"Gradual terrain incline ({val_str}{unit_str}) allows natural infiltration rather than rapid surface surge."
            elif "Elevation" in feature_name:
                return f"Higher catchment terrain ({val_str}{unit_str}) provides natural topographic elevation above the flood plane."
            else:
                return f"{feature_name} observed at {val_str}{unit_str} acted to temper the flood forecast (-{abs(shap_value):.3f} SHAP)."
