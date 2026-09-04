"""
===============================================================================
PRAVAH — Standalone Machine Learning Diagnostic & Stress-Testing Script
===============================================================================
Usage:
    python test_ml.py
    python test_ml.py --model models/task_a_onset_LightGBM.joblib
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pravah.ml_diagnostic")

# Default fallback model paths in repository
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "task_a_onset_LightGBM.joblib"
ALT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "task_a_onset_RandomForest.joblib"


def load_model_bundle(model_path: Path) -> Dict[str, Any]:
    """
    Safely load a serialized PRAVAH joblib bundle containing the trained model,
    feature column names, and decision threshold.
    """
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found at: {model_path}")

    logger.info("Loading model artifact from: %s", model_path.name)
    loaded = joblib.load(model_path)

    if isinstance(loaded, dict):
        bundle = loaded
    else:
        bundle = {
            "model": loaded,
            "feature_cols": getattr(loaded, "feature_names_in_", None),
            "threshold": 0.50,
        }

    return bundle


def generate_synthetic_features(feature_cols: List[str]) -> pd.DataFrame:
    """
    Synthesize realistic hydrodynamic and antecedent meteorological features
    specifically tuned for the Maharashtra Western Ghats terrain.
    """
    data: Dict[str, Any] = {}

    for col in feature_cols:
        col_lower = col.lower()

        # Antecedent precipitation features
        if "rain_1d" in col_lower:
            data[col] = [68.5]  # Heavy monsoonal burst (68.5 mm/day)
        elif "rain_2d_sum" in col_lower:
            data[col] = [124.0]
        elif "rain_3d_sum" in col_lower or "rain_3d_cum" in col_lower:
            data[col] = [185.2]
        elif "rain_5d_sum" in col_lower:
            data[col] = [260.0]
        elif "rain_7d_sum" in col_lower or "rain_7d_cum" in col_lower:
            data[col] = [340.5]
        elif "rain_10d_sum" in col_lower:
            data[col] = [425.0]
        elif "rain_3d_max" in col_lower:
            data[col] = [85.0]
        elif "rain_7d_max" in col_lower:
            data[col] = [95.5]
        elif "rain_dry_days" in col_lower:
            data[col] = [0.0]
        elif "gpm" in col_lower:
            data[col] = [1]
        
        # Catchment topography features
        elif "elevation" in col_lower:
            data[col] = [560.0]  # Western Ghats elevation (m)
        elif "slope" in col_lower:
            data[col] = [14.2]   # Steep riparian incline (%)
        elif "drainage" in col_lower or "length" in col_lower:
            data[col] = [45.8]
        elif "area" in col_lower:
            data[col] = [1250.0] # Catchment surface area (km2)
        elif "warning_level" in col_lower:
            data[col] = [540.0]
        elif "danger_level" in col_lower:
            data[col] = [544.0]
        
        # Categorical / metadata features
        elif any(k in col_lower for k in ["station", "river", "basin", "state", "privacy"]):
            data[col] = ["Karad"] if "station" in col_lower else ["Krishna"] if "river" in col_lower else ["Maharashtra"]
        else:
            data[col] = [1.0]

    return pd.DataFrame(data)


def run_model_diagnostic(model_path: Path) -> bool:
    """
    Executes a complete verification cycle with feature mismatch debugging.
    """
    print("\n" + "=" * 78)
    print(" 🌊 PRAVAH — Machine Learning Pipeline Diagnostic (SIH 2026)")
    print("=" * 78)

    # 1. Load Model Bundle
    try:
        bundle = load_model_bundle(model_path)
    except Exception as exc:
        logger.error("Failed to load model artifact: %s", exc)
        return False

    model = bundle.get("model")
    feature_cols = bundle.get("feature_cols")
    threshold = float(bundle.get("threshold", 0.50))

    if model is None:
        logger.error("Bundle does not contain a valid 'model' estimator.")
        return False

    if feature_cols is None:
        if hasattr(model, "feature_names_in_"):
            feature_cols = list(model.feature_names_in_)
        elif hasattr(model, "steps") and hasattr(model.steps[0][1], "feature_names_in_"):
            feature_cols = list(model.steps[0][1].feature_names_in_)
        else:
            logger.warning("Feature column names not serialized; attempting generic feature set.")
            feature_cols = ["rain_1d", "rain_3d_sum", "rain_7d_sum", "rain_10d_sum", "elevation_mean", "slope_mean"]

    print(f"\n[Artifact Info]")
    print(f"  • Model Type      : {type(model).__name__}")
    print(f"  • Tuned Threshold : {threshold:.4f} (Decision boundary for alert triggering)")
    print(f"  • Feature Count   : {len(feature_cols)} expected input variables")

    # 2. Construct Synthetic Test DataFrame
    df_test = generate_synthetic_features(feature_cols)

    # 3. Model Inference & Probabilities
    print("\n[Inference Stress-Test]")
    try:
        probs = model.predict_proba(df_test)
        prob_no_flood = float(probs[0, 0])
        prob_flood = float(probs[0, 1])

        alert_tier = "EMERGENCY" if prob_flood >= threshold * 1.5 else "WARNING" if prob_flood >= threshold else "NORMAL"

        print(f"  • Input Shape     : {df_test.shape} (1 row, {df_test.shape[1]} features)")
        print(f"  • Prob [Class 0]  : {prob_no_flood * 100:.2f}% (No Flood)")
        print(f"  • Prob [Class 1]  : {prob_flood * 100:.2f}% (Flood Onset Risk)")
        print(f"  • Target Tier     : {alert_tier}")
        print("\n PREDICT_PROBA SUCCEEDED: Model pipeline is production-stable!")

    except ValueError as exc:
        print("\n FEATURE SCHEMA MISMATCH DETECTED!")
        print("-" * 78)
        print(f"Raw Exception Message:\n{exc}")
        print("-" * 78)

        if hasattr(model, "feature_names_in_"):
            expected_set = set(model.feature_names_in_)
            provided_set = set(df_test.columns)

            missing = expected_set - provided_set
            extra = provided_set - expected_set

            if missing:
                print(f"\nMissing Features ({len(missing)}):")
                for m in sorted(missing)[:10]:
                    print(f"  -  {m}")
                if len(missing) > 10:
                    print(f"  ... and {len(missing) - 10} more.")

            if extra:
                print(f"\nUnexpected Extra Features ({len(extra)}):")
                for e in sorted(extra)[:10]:
                    print(f"  -  {e}")

        print("\nRemediation Tip:")
        print("Ensure input DataFrames are transformed via the identical ColumnTransformer")
        print("or select only the exact `bundle['feature_cols']` before calling predict_proba().")
        return False

    except Exception as exc:
        logger.error("Unexpected inference error: %s", exc, exc_info=True)
        return False

    print("=" * 78 + "\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PRAVAH ML Diagnostic Test")
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH if DEFAULT_MODEL_PATH.exists() else ALT_MODEL_PATH,
        help="Path to .joblib model bundle",
    )
    args = parser.parse_args()

    success = run_model_diagnostic(args.model)
    sys.exit(0 if success else 1)
