from __future__ import annotations

import abc
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import shap

logger = logging.getLogger("pravah.xai")


class BaseExplainer(abc.ABC):
    """
    Abstract base class for model-specific SHAP TreeExplainers.
    Wraps the underlying estimator, calculates Shapley values, and handles
    classifier-specific output dimensions and expected baseline calibrations.
    """

    def __init__(self, classifier: Any, feature_names: List[str], model_name: str):
        self.classifier = classifier
        self.feature_names = list(feature_names)
        self.model_name = model_name
        self._explainer: Optional[shap.TreeExplainer] = None
        self._init_explainer()

    @abc.abstractmethod
    def _init_explainer(self) -> None:
        """Initialize the model-specific TreeExplainer."""
        pass

    @abc.abstractmethod
    def explain_instance(
        self, X_transformed: np.ndarray, raw_features_dict: Dict[str, Any]
    ) -> Tuple[float, np.ndarray, float]:
        """
        Explain a single preprocessed observation vector.
        Returns:
            predicted_prob: float [0.0, 1.0]
            shap_values: 1D np.ndarray of shape (num_features,) for class 1 (flood risk)
            base_value: float expected baseline value
        """
        pass

    def get_global_feature_importance(self, X_background: np.ndarray) -> np.ndarray:
        """
        Compute mean absolute SHAP value for each feature across a representative sample.
        Returns:
            1D np.ndarray of shape (num_features,)
        """
        if self._explainer is None:
            raise RuntimeError("TreeExplainer is not initialized.")

        raw_shap = self._explainer.shap_values(X_background)
        # Extract class 1
        if isinstance(raw_shap, list) and len(raw_shap) == 2:
            class1_shap = raw_shap[1]
        elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 3:
            class1_shap = raw_shap[:, :, 1]
        else:
            class1_shap = raw_shap

        mean_abs = np.mean(np.abs(class1_shap), axis=0)
        return mean_abs
