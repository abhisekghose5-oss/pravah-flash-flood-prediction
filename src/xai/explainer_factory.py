from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from src.xai.explainers.base_explainer import BaseExplainer
from src.xai.explainers.lightgbm_explainer import LightGBMExplainer
from src.xai.explainers.random_forest_explainer import RandomForestExplainer
from src.xai.explainers.xgboost_explainer import XGBoostExplainer

logger = logging.getLogger("pravah.xai.factory")


class ExplainerFactory:
    """
    Factory creating and caching model-specific SHAP TreeExplainers.
    Reuses existing explainer instances to avoid redundant graph recompilations.
    """

    _cache: Dict[str, BaseExplainer] = {}
    _lock = threading.Lock()

    @classmethod
    def get_explainer(
        cls,
        model_name: str,
        classifier: Any,
        feature_names: List[str],
        task: str = "onset",
    ) -> BaseExplainer:
        """
        Retrieve or instantiate an appropriate BaseExplainer for the given classifier.
        Keyed by f"{model_name}_{task}".
        """
        norm_name = str(model_name).strip()
        key = f"{norm_name}_{task}".lower()

        with cls._lock:
            if key in cls._cache:
                return cls._cache[key]

            lower = norm_name.lower()
            if "random" in lower or "rf" in lower:
                explainer = RandomForestExplainer(classifier, feature_names)
            elif "xgb" in lower:
                explainer = XGBoostExplainer(classifier, feature_names)
            elif "light" in lower or "lgbm" in lower:
                explainer = LightGBMExplainer(classifier, feature_names)
            else:
                # Attempt to inspect estimator class name
                cls_name = classifier.__class__.__name__.lower()
                if "forest" in cls_name:
                    explainer = RandomForestExplainer(classifier, feature_names)
                elif "xgb" in cls_name:
                    explainer = XGBoostExplainer(classifier, feature_names)
                elif "lgbm" in cls_name:
                    explainer = LightGBMExplainer(classifier, feature_names)
                else:
                    raise ValueError(
                        f"Unsupported model architecture '{model_name}'. "
                        "Supported models are: 'RandomForest', 'XGBoost', 'LightGBM'."
                    )

            cls._cache[key] = explainer
            logger.info("Cached new TreeExplainer for key: %s", key)
            return explainer

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cached explainers (useful for unit testing)."""
        with cls._lock:
            cls._cache.clear()
