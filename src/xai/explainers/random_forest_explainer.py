from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple
import numpy as np
import shap

from src.xai.explainers.base_explainer import BaseExplainer

logger = logging.getLogger("pravah.xai.rf")


class RandomForestExplainer(BaseExplainer):
    """
    SHAP TreeExplainer implementation tailored for scikit-learn RandomForestClassifier.
    Calculates Shapley values in probability space for binary flood onset classification.
    """

    def __init__(self, classifier: Any, feature_names: List[str]):
        super().__init__(classifier, feature_names, model_name="RandomForest")

    def _init_explainer(self) -> None:
        try:
            # RandomForestClassifier outputs probability values for each class
            self._explainer = shap.TreeExplainer(self.classifier)
            logger.info("RandomForest SHAP TreeExplainer initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize RandomForest TreeExplainer: %s", e)
            raise

    def explain_instance(
        self, X_transformed: np.ndarray, raw_features_dict: Dict[str, Any]
    ) -> Tuple[float, np.ndarray, float]:
        if self._explainer is None:
            raise RuntimeError("RandomForest TreeExplainer not initialized.")

        # Ensure 2D input
        if X_transformed.ndim == 1:
            X_arr = X_transformed.reshape(1, -1)
        else:
            X_arr = X_transformed

        # 1. Model predicted probability for Class 1 (Flood Onset)
        prob = float(self.classifier.predict_proba(X_arr)[0, 1])

        # 2. Extract SHAP values
        raw_shap = self._explainer.shap_values(X_arr)

        # In shap 0.50+, shape may be (1, N, 2) or list of 2 arrays [ (1, N), (1, N) ]
        if isinstance(raw_shap, list) and len(raw_shap) >= 2:
            shap_class1 = np.asarray(raw_shap[1]).flatten()
        elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 3 and raw_shap.shape[2] >= 2:
            shap_class1 = raw_shap[0, :, 1]
        elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 2:
            shap_class1 = raw_shap[0]
        else:
            shap_class1 = np.asarray(raw_shap).flatten()

        # 3. Base expected value E[f(x)]
        ev = self._explainer.expected_value
        if isinstance(ev, (list, np.ndarray)):
            base_val = float(ev[1] if len(ev) > 1 else ev[0])
        else:
            base_val = float(ev)

        return prob, shap_class1, base_val
