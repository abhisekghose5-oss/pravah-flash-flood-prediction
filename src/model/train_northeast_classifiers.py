"""
train_northeast_classifiers.py

Trains dual-task boosted tree classifiers (LightGBM, XGBoost, Random Forest)
on the Northeast master spatio-temporal grid for:
- Task A: Flood Onset Prediction within 24h lead time
- Task B: Active / Sustained Inundation Persistence

Optimizes decision thresholds for Critical Success Index (CSI / Threat Score)
and saves serializations non-destructively to models/*_ne.joblib and models/thresholds_ne.json.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pravah.train_ne")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "data" / "processed" / "northeast" / "ne_master_daily_grid.parquet"
MODELS_DIR = REPO_ROOT / "models"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "northeast"
METRICS_PATH = OUTPUT_DIR / "ne_evaluation_metrics.json"
THRESHOLDS_PATH = MODELS_DIR / "thresholds_ne.json"


def build_ne_model_columns(df: pd.DataFrame) -> List[str]:
    """Select usable predictor features while strictly excluding identifiers and labels."""
    exclude = {
        "GaugeID",
        "Date",
        "Station",
        "River_Name",
        "Basin",
        "State",
        "District",
        "Privacy",
        "split",
        "target_onset",
        "target_active",
        "target_peak",
        "water_level_m",
        "water_level_max_m",
        "water_level_observations",
    }
    feature_cols = [c for c in df.columns if c not in exclude]

    usable_cols = []
    for col in feature_cols:
        series = df[col]
        if series.isna().all():
            continue
        if series.dropna().nunique() <= 1:
            continue
        usable_cols.append(col)

    return usable_cols


def make_preprocessor(X_train: pd.DataFrame) -> ColumnTransformer:
    """Construct median imputer + standard scaler for numerics and one-hot encoder for categoricals."""
    numeric_cols = list(X_train.select_dtypes(include=["number"]).columns)
    categorical_cols = [c for c in X_train.columns if c not in numeric_cols]

    transformers = []
    if numeric_cols:
        transformers.append(
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_cols,
            )
        )
    if categorical_cols:
        transformers.append(
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_cols,
            )
        )

    return ColumnTransformer(transformers=transformers, remainder="drop")


def get_confusion(pred: np.ndarray, y_true: np.ndarray) -> Tuple[int, int, int, int]:
    tp = int(np.sum((pred == 1) & (y_true == 1)))
    tn = int(np.sum((pred == 0) & (y_true == 0)))
    fp = int(np.sum((pred == 1) & (y_true == 0)))
    fn = int(np.sum((pred == 0) & (y_true == 1)))
    return tp, tn, fp, fn


def calculate_csi(pred: np.ndarray, y_true: np.ndarray) -> float:
    """Critical Success Index (CSI / Threat Score) = TP / (TP + FP + FN)."""
    tp, _, fp, fn = get_confusion(pred, y_true)
    denom = tp + fp + fn
    return float(tp / denom) if denom > 0 else 0.0


def sweep_csi_threshold(y_true: np.ndarray, proba: np.ndarray, min_recall: float = 0.50) -> float:
    """
    Sweep decision thresholds p in [0.05, 0.50] targeting the maximum Critical Success Index (CSI).
    """
    thresholds = np.linspace(0.05, 0.50, 451)
    best_threshold = 0.20
    best_csi = -1.0

    for threshold in thresholds:
        pred = (proba >= threshold).astype(int)
        tp, _, fp, fn = get_confusion(pred, y_true)
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        csi = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0

        if recall < min_recall:
            continue

        if csi > best_csi:
            best_csi = csi
            best_threshold = float(threshold)

    # Fallback to unconditional highest CSI if minimum recall constraint was unmet
    if best_csi < 0.0:
        for threshold in thresholds:
            pred = (proba >= threshold).astype(int)
            tp, _, fp, fn = get_confusion(pred, y_true)
            csi = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0
            if csi > best_csi:
                best_csi = csi
                best_threshold = float(threshold)

    return float(best_threshold)


def evaluate_test_metrics(y_true: np.ndarray, proba: np.ndarray, threshold: float) -> Dict[str, Any]:
    """Compute comprehensive operational verification metrics including CSI, POD, and FAR."""
    pred = (proba >= threshold).astype(int)
    tp, tn, fp, fn = get_confusion(pred, y_true)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    pod = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # Probability of Detection / Recall
    far = fp / (tp + fp) if (tp + fp) > 0 else 0.0  # False Alarm Ratio
    csi = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    f1 = 2 * precision * pod / (precision + pod) if (precision + pod) > 0 else 0.0
    roc_auc = float(roc_auc_score(y_true, proba))
    ap = float(average_precision_score(y_true, proba))

    return {
        "threshold": round(float(threshold), 4),
        "csi": round(float(csi), 4),
        "pod": round(float(pod), 4),
        "recall": round(float(pod), 4),
        "far": round(float(far), 4),
        "precision": round(float(precision), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(ap), 4),
        "hits_tp": int(tp),
        "false_alarms_fp": int(fp),
        "misses_fn": int(fn),
        "correct_negatives_tn": int(tn),
        "positives_predicted": int(pred.sum()),
    }


def make_ne_classifier(model_name: str, pos_weight: float) -> Pipeline:
    """Create configured classifier with cost-sensitive weighting for extreme class imbalance."""
    if model_name == "LightGBM":
        estimator = LGBMClassifier(
            objective="binary",
            n_estimators=350,
            learning_rate=0.03,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=pos_weight,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    elif model_name == "XGBoost":
        estimator = XGBClassifier(
            objective="binary:logistic",
            n_estimators=350,
            learning_rate=0.03,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=pos_weight,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
        )
    elif model_name == "RandomForest":
        estimator = RandomForestClassifier(
            n_estimators=200,
            random_state=42,
            class_weight="balanced_subsample",
            min_samples_leaf=5,
            n_jobs=-1,
        )
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    return Pipeline(steps=[("preprocessor", None), ("classifier", estimator)])


def train_and_evaluate_ne_task(
    task_key: str,
    target_col: str,
    df: pd.DataFrame,
    feature_cols: List[str]
) -> Dict[str, Any]:
    """Train all 3 model families on the task, optimize thresholds for CSI, and save models."""
    logger.info("=== Starting Northeast Training for %s (%s) ===", task_key, target_col)

    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()

    # Apply controlled dry-day sub-sampling on train_df to achieve ~1:30 to 1:50 ratio
    pos_mask = (train_df[target_col] > 0)
    neg_mask = ~pos_mask
    n_pos = pos_mask.sum()

    # Retain all rainy days (rain_1d > 10.0 or rain_3d_sum > 25.0) plus sample of dry days
    rainy_neg_mask = neg_mask & ((train_df["rain_1d"] > 10.0) | (train_df["rain_3d_sum"] > 25.0))
    dry_neg_mask = neg_mask & ~rainy_neg_mask

    target_dry_sample = min(len(train_df[dry_neg_mask]), max(int(n_pos * 30), 5000))
    sampled_dry = train_df[dry_neg_mask].sample(n=target_dry_sample, random_state=42)

    sampled_train_df = pd.concat([train_df[pos_mask], train_df[rainy_neg_mask], sampled_dry]).sample(frac=1.0, random_state=42)
    logger.info("[%s] Resampled training set: %d rows (%d positive, %d negative)",
                task_key, len(sampled_train_df), sampled_train_df[target_col].sum(),
                len(sampled_train_df) - sampled_train_df[target_col].sum())

    X_train = sampled_train_df[feature_cols].copy()
    y_train = (sampled_train_df[target_col] > 0).astype(int).to_numpy()

    X_val = val_df[feature_cols].copy()
    y_val = (val_df[target_col] > 0).astype(int).to_numpy()

    X_test = test_df[feature_cols].copy()
    y_test = (test_df[target_col] > 0).astype(int).to_numpy()

    # Cost-sensitive weight: negative / positive count
    neg_count = int(np.sum(y_train == 0))
    pos_count = max(int(np.sum(y_train == 1)), 1)
    pos_weight = min(float(neg_count / pos_count), 50.0)

    task_results = {}

    for model_name, file_prefix in [("LightGBM", "lgbm"), ("XGBoost", "xgb"), ("RandomForest", "rf")]:
        logger.info("[%s] Training %s (scale_pos_weight=%.1f)...", task_key, model_name, pos_weight)
        pipeline = make_ne_classifier(model_name, pos_weight)
        preprocessor = make_preprocessor(X_train)
        pipeline.steps[0] = ("preprocessor", preprocessor)

        pipeline.fit(X_train, y_train)

        # Validation CSI threshold optimization
        val_proba = pipeline.predict_proba(X_val)[:, 1]
        threshold = sweep_csi_threshold(y_val, val_proba, min_recall=0.50)

        # Evaluation on held-out test set
        test_proba = pipeline.predict_proba(X_test)[:, 1]
        metrics = evaluate_test_metrics(y_test, test_proba, threshold)
        metrics["val_threshold"] = round(float(threshold), 4)

        task_results[model_name] = metrics
        logger.info("[%s - %s] Test CSI=%.4f | POD(Recall)=%.4f | FAR=%.4f | Precision=%.4f | F1=%.4f | Opt Threshold=%.4f",
                    task_key, model_name, metrics["csi"], metrics["pod"], metrics["far"], metrics["precision"], metrics["f1"], threshold)

        # Non-destructive serialization to models/
        artifact_filename = f"{file_prefix}_{task_key}_ne.joblib"
        out_path = MODELS_DIR / artifact_filename
        joblib.dump(
            {
                "model": pipeline,
                "threshold": threshold,
                "feature_cols": feature_cols,
                "metrics": metrics,
                "region": "Northeast",
                "task": task_key,
                "model_name": model_name,
            },
            out_path,
            compress=3,
        )
        logger.info("Saved Northeast model artifact: %s", out_path)

    return task_results


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading Northeast Master Grid from %s...", DATASET_PATH)
    df = pd.read_parquet(DATASET_PATH)
    feature_cols = build_ne_model_columns(df)
    logger.info("Identified %d usable predictor feature columns for Northeast", len(feature_cols))

    all_metrics: Dict[str, Any] = {}
    thresholds_config: Dict[str, Any] = {}

    # Task A: Flood Onset
    task_a_metrics = train_and_evaluate_ne_task("task_a", "target_onset", df, feature_cols)
    all_metrics["task_a_onset_ne"] = task_a_metrics

    # Task B: Active Flood Persistence
    task_b_metrics = train_and_evaluate_ne_task("task_b", "target_active", df, feature_cols)
    all_metrics["task_b_active_ne"] = task_b_metrics

    # Extract threshold dictionary
    for task_k, task_m in all_metrics.items():
        thresholds_config[task_k] = {
            m_name: m_stats["threshold"] for m_name, m_stats in task_m.items()
        }

    # Save metrics JSON
    with METRICS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(all_metrics, fh, indent=2)
    logger.info("Exported Northeast evaluation metrics to %s", METRICS_PATH)

    # Save thresholds JSON
    with THRESHOLDS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(thresholds_config, fh, indent=2)
    logger.info("Exported Northeast optimal thresholds to %s", THRESHOLDS_PATH)

    print("\n=======================================================")
    print("      NORTHEAST ML ENGINE TRAINING COMPLETE")
    print("=======================================================")
    for task_name, task_dict in all_metrics.items():
        print(f"\n--- {task_name.upper()} ---")
        for model_name, metrics in task_dict.items():
            print(f"  [{model_name:12s}] CSI: {metrics['csi']:.4f} | POD: {metrics['pod']:.4f} | FAR: {metrics['far']:.4f} | Prec: {metrics['precision']:.4f} | F1: {metrics['f1']:.4f} | Thresh: {metrics['threshold']:.4f}")


if __name__ == "__main__":
    main()
