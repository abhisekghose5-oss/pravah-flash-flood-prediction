from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple
import numpy as np
import shap

from src.xai.explainers.base_explainer import BaseExplainer

logger = logging.getLogger("pravah.xai.xgb")


class XGBoostExplainer(BaseExplainer):
    """
    SHAP TreeExplainer implementation tailored for XGBoost (XGBClassifier).
    Computes feature contributions for gradient boosted tree structures.
    """

    def __init__(self, classifier: Any, feature_names: List[str]):
        super().__init__(classifier, feature_names, model_name="XGBoost")

    def _init_explainer(self) -> None:
        try:
            self._explainer = shap.TreeExplainer(self.classifier)
            logger.info("XGBoost SHAP TreeExplainer initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize XGBoost TreeExplainer: %s", e)
            raise

    def explain_instance(
        self, X_transformed: np.ndarray, raw_features_dict: Dict[str, Any]
    ) -> Tuple[float, np.ndarray, float]:
        if self._explainer is None:
            raise RuntimeError("XGBoost TreeExplainer not initialized.")

        # Ensure 2D input
        if X_transformed.ndim == 1:
            X_arr = X_transformed.reshape(1, -1)
        else:
            X_arr = X_transformed

        # 1. Model predicted probability
        prob = float(self.classifier.predict_proba(X_arr)[0, 1])

        # 2. Extract SHAP values
        raw_shap = self._explainer.shap_values(X_arr)

        if isinstance(raw_shap, list) and len(raw_shap) >= 2:
            shap_class1 = np.asarray(raw_shap[1]).flatten()
        elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 3 and raw_shap.shape[2] >= 2:
            shap_class1 = raw_shap[0, :, 1]
        elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 2:
            shap_class1 = raw_shap[0]
        else:
            shap_class1 = np.asarray(raw_shap).flatten()

        # 3. Base expected value
        ev = self._explainer.expected_value
        if isinstance(ev, (list, np.ndarray)):
            base_val = float(ev[1] if len(ev) > 1 else ev[0])
        else:
            base_val = float(ev)

        return prob, shap_class1, base_val
