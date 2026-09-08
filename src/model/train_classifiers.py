from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    matplotlib = None
    plt = None
    HAS_MATPLOTLIB = False
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

import joblib
from src.model.baseline_flood_model import build_model_columns

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "data" / "processed" / "master_daily_grid_splits.parquet"
OUTPUT_DIR = REPO_ROOT / "data" / "processed"
MODELS_DIR = REPO_ROOT / "models"
METRICS_PATH = OUTPUT_DIR / "model_evaluation_metrics.json"


def make_preprocessor(X_train: pd.DataFrame) -> ColumnTransformer:
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


def make_model(model_name: str) -> Pipeline:
    if model_name == "RandomForest":
        estimator = RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced_subsample",
            min_samples_leaf=5,
        )
    elif model_name == "LightGBM":
        estimator = LGBMClassifier(
            objective="binary",
            n_estimators=500,
            learning_rate=0.03,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=700,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    elif model_name == "XGBoost":
        estimator = XGBClassifier(
            objective="binary:logistic",
            n_estimators=500,
            learning_rate=0.03,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=700,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
            use_label_encoder=False,
        )
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    return Pipeline(steps=[("preprocessor", None), ("classifier", estimator)])


def get_confusion(pred: np.ndarray, y_true: np.ndarray) -> tuple[int, int, int, int]:
    tp = int(np.sum((pred == 1) & (y_true == 1)))
    tn = int(np.sum((pred == 0) & (y_true == 0)))
    fp = int(np.sum((pred == 1) & (y_true == 0)))
    fn = int(np.sum((pred == 0) & (y_true == 1)))
    return tp, tn, fp, fn


def csi_score(pred: np.ndarray, y_true: np.ndarray) -> float:
    tp, _, fp, fn = get_confusion(pred, y_true)
    denom = tp + fp + fn
    return float(tp / denom) if denom else 0.0


def select_model_for_task(metrics: dict[str, dict]) -> str:
    """Pick the most operationally useful genuine-data model.

    This penalizes models that chase recall at the expense of precision so that the
    recommended model remains useful in deployment rather than only maximizing one
    metric on a highly imbalanced flood dataset.
    """
    eligible: dict[str, float] = {}
    for model_name, stats in metrics.items():
        precision = float(stats.get("precision", 0.0) or 0.0)
        recall = float(stats.get("recall", 0.0) or 0.0)
        f1 = float(stats.get("f1", 0.0) or 0.0)
        csi = float(stats.get("csi", 0.0) or 0.0)

        if precision < 0.02 or recall < 0.08:
            continue

        score = 0.45 * f1 + 0.25 * csi + 0.20 * precision + 0.10 * recall
        eligible[model_name] = score

    if not eligible:
        return max(
            metrics,
            key=lambda model_name: (
                float(metrics[model_name].get("f1", 0.0) or 0.0),
                float(metrics[model_name].get("precision", 0.0) or 0.0),
                float(metrics[model_name].get("recall", 0.0) or 0.0),
            ),
        )

    return max(eligible, key=eligible.get)


def select_threshold(y_true: np.ndarray, proba: np.ndarray, min_recall: float = 0.75) -> float:
    thresholds = np.linspace(0.0, 1.0, 2001)
    best_threshold = 0.5
    best_score = -1.0
    best_recall = -1.0
    best_precision = -1.0

    for threshold in thresholds:
        pred = (proba >= threshold).astype(int)
        tp, _, fp, fn = get_confusion(pred, y_true)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        csi = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0

        if recall < min_recall:
            continue

        candidate = (csi, recall, precision)
        if candidate > (best_score, best_recall, best_precision):
            best_threshold = float(threshold)
            best_score = float(csi)
            best_recall = float(recall)
            best_precision = float(precision)

    if best_score < 0.0:
        for threshold in thresholds:
            pred = (proba >= threshold).astype(int)
            tp, _, fp, fn = get_confusion(pred, y_true)
            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall = tp / (tp + fn) if (tp + fn) else 0.0
            csi = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0
            candidate = (csi, recall, precision)
            if candidate > (best_score, best_recall, best_precision):
                best_threshold = float(threshold)
                best_score = float(csi)
                best_recall = float(recall)
                best_precision = float(precision)

    return float(best_threshold)


def evaluate_predictions(y_true: np.ndarray, proba: np.ndarray, threshold: float) -> dict:
    pred = (proba >= threshold).astype(int)
    precision = precision_score(y_true, pred, zero_division=0)
    recall = recall_score(y_true, pred, zero_division=0)
    f1 = f1_score(y_true, pred, zero_division=0)
    csi = csi_score(pred, y_true)
    ap = average_precision_score(y_true, proba)
    roc = roc_auc_score(y_true, proba)
    return {
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "csi": float(csi),
        "roc_auc": float(roc),
        "average_precision": float(ap),
        "positive_count": int(pred.sum()),
    }


def save_feature_importance(model: Pipeline, preprocessor: ColumnTransformer, model_name: str, task_name: str) -> pd.DataFrame:
    feature_names = preprocessor.get_feature_names_out()
    classifier = model.named_steps["classifier"]
    importances = classifier.feature_importances_
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importances,
    }).sort_values("importance", ascending=False)

    top15 = importance_df.head(15).reset_index(drop=True)
    out_path = OUTPUT_DIR / f"feature_importance_{task_name}_{model_name}.csv"
    top15.to_csv(out_path, index=False)

    if HAS_MATPLOTLIB and plt is not None:
        plt.figure(figsize=(10, 8))
        plt.barh(top15["feature"].tolist()[::-1], top15["importance"].tolist()[::-1], color="steelblue")
        plt.gca().invert_yaxis()
        plt.title(f"Top 15 Feature Importances: {task_name} - {model_name}")
        plt.xlabel("Importance")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / f"feature_importance_{task_name}_{model_name}.png", dpi=200)
        plt.close()
    return top15


def run_task(task_name: str, target_col: str) -> dict[str, dict]:
    df = pd.read_parquet(DATASET_PATH)
    feature_cols = build_model_columns(df)

    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()

    y_train = (train_df[target_col] > 0).astype(int).to_numpy()
    y_val = (val_df[target_col] > 0).astype(int).to_numpy()
    y_test = (test_df[target_col] > 0).astype(int).to_numpy()

    X_train = train_df[feature_cols].copy()
    X_val = val_df[feature_cols].copy()
    X_test = test_df[feature_cols].copy()

    all_results: dict[str, dict] = {}
    for model_name in ["RandomForest", "LightGBM", "XGBoost"]:
        model = make_model(model_name)
        preprocessor = make_preprocessor(X_train)
        model.steps[0] = ("preprocessor", preprocessor)
        model.fit(X_train, y_train)

        val_proba = model.predict_proba(X_val)[:, 1]
        threshold = select_threshold(y_val, val_proba, min_recall=0.75)
        test_proba = model.predict_proba(X_test)[:, 1]

        metrics = evaluate_predictions(y_test, test_proba, threshold)
        metrics["val_threshold"] = float(threshold)
        metrics["val_roc_auc"] = float(roc_auc_score(y_val, val_proba))
        metrics["val_average_precision"] = float(average_precision_score(y_val, val_proba))
        metrics["val_precision_recall_curve"] = None
        metrics["top_15_features"] = save_feature_importance(model, preprocessor, model_name, task_name).to_dict(orient="records")
        all_results[model_name] = metrics

        model_path = MODELS_DIR / f"{task_name}_{model_name}.joblib"
        joblib.dump({"model": model, "threshold": threshold, "feature_cols": feature_cols, "metrics": metrics}, model_path, compress=3)
        print(f"Saved trained model to: {model_path}")

    return all_results


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {}
    for task_name, target_col in {
        "task_a_onset": "target_onset",
        "task_b_active": "target_active",
    }.items():
        payload[task_name] = run_task(task_name, target_col)

    with METRICS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print("Saved evaluation metrics to:", METRICS_PATH)
    recommended = {
        task_name: select_model_for_task(task_results)
        for task_name, task_results in payload.items()
    }
    print("Recommended models:", recommended)
    for task_name, task_results in payload.items():
        print(f"\n{task_name}")
        row_data = []
        for model_name, metrics in task_results.items():
            row_data.append(
                {
                    "model": model_name,
                    "threshold": round(metrics["threshold"], 4),
                    "precision": round(metrics["precision"], 4),
                    "recall": round(metrics["recall"], 4),
                    "f1": round(metrics["f1"], 4),
                    "csi": round(metrics["csi"], 4),
                    "roc_auc": round(metrics["roc_auc"], 4),
                    "average_precision": round(metrics["average_precision"], 4),
                    "positive_count": metrics["positive_count"],
                }
            )
        print(pd.DataFrame(row_data).to_string(index=False))


if __name__ == "__main__":
    main()
