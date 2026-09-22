from __future__ import annotations

from typing import Any, Dict, List, Tuple
import numpy as np

from src.xai.feature_mapper import FeatureMapper
from src.xai.models.explanation import (
    FeatureContribution,
    ForcePlotData,
    GlobalSummaryFeature,
)


def compute_relative_contributions(shap_values: np.ndarray) -> np.ndarray:
    """
    Calculate normalized contribution percentages (0 to 100%) for each feature
    based on the total absolute attribution mass:
        rel_contrib_i = (|phi_i| / sum_j |phi_j|) * 100
    """
    arr = np.asarray(shap_values, dtype=float)
    total_abs = np.sum(np.abs(arr))
    if total_abs <= 1e-12:
        return np.zeros_like(arr)
    return np.round((np.abs(arr) / total_abs) * 100.0, 2)


def build_feature_contributions(
    feature_names: List[str],
    shap_values: np.ndarray,
    input_values: Dict[str, Any],
) -> List[FeatureContribution]:
    """
    Construct enriched FeatureContribution objects for all features.
    """
    rel_pcts = compute_relative_contributions(shap_values)
    contributions: List[FeatureContribution] = []

    for i, raw_key in enumerate(feature_names):
        shap_val = float(shap_values[i])
        clean_k = FeatureMapper.clean_key(raw_key)
        friendly_name, unit, domain_cat = FeatureMapper.get_metadata(raw_key)

        # Lookup input value
        val = input_values.get(raw_key, input_values.get(clean_k, 0.0))
        if isinstance(val, (np.floating, float)):
            val = round(float(val), 2)
        elif isinstance(val, (np.integer, int)):
            val = int(val)

        direction = "increases_risk" if shap_val > 0 else "decreases_risk"
        human_expl = FeatureMapper.generate_human_explanation(
            friendly_name, val, shap_val, direction, unit
        )

        contributions.append(
            FeatureContribution(
                feature_key=clean_k,
                feature_name=friendly_name,
                feature_value=val,
                shap_value=round(shap_val, 4),
                direction=direction,
                relative_contribution=float(rel_pcts[i]),
                unit=unit,
                domain_category=domain_cat,
                human_explanation=human_expl,
            )
        )

    # Sort descending by absolute impact
    contributions.sort(key=lambda x: abs(x.shap_value), reverse=True)
    return contributions


def generate_headline_narrative(
    prob: float,
    threshold: float,
    risk_tier: str,
    top_pos: List[FeatureContribution],
    top_neg: List[FeatureContribution],
) -> Tuple[str, str]:
    """
    Generate the dynamic headline title ("WHY HIGH RISK?", "WHY MODERATE RISK?", "WHY LOW RISK?")
    and human-readable narrative synthesis.
    """
    pct_str = f"{prob * 100:.1f}%"

    if risk_tier in ("EMERGENCY", "WARNING") or prob >= threshold:
        title = "WHY HIGH RISK?"
        if top_pos:
            factors_str = " and ".join(
                f"{f.feature_name} ({'+' if f.shap_value > 0 else ''}{f.relative_contribution:.0f}% impact)"
                for f in top_pos[:2]
            )
            narrative = (
                f"Elevated flood onset probability ({pct_str}) is primarily driven by {factors_str}. "
                "These factors indicate rapid catchment saturation exceeding threshold drainage limits."
            )
        else:
            narrative = f"Elevated flood risk probability of {pct_str} exceeds the tuned decision threshold of {threshold:.2f}."

    elif risk_tier == "ADVISORY" or prob >= 0.5 * threshold:
        title = "WHY MODERATE RISK?"
        pos_factor = top_pos[0].feature_name if top_pos else "antecedent rainfall"
        neg_factor = top_neg[0].feature_name if top_neg else "moderate river storage"
        narrative = (
            f"Catchment exhibits moderate hydrological sensitivity ({pct_str}). While {pos_factor} exerts "
            f"upward pressure, stabilizing conditions such as {neg_factor} maintain the river corridor below critical danger."
        )

    else:
        title = "WHY LOW RISK?"
        if top_neg:
            factors_str = " and ".join(
                f"{f.feature_name} (-{f.relative_contribution:.0f}% impact)"
                for f in top_neg[:2]
            )
            narrative = (
                f"Flood onset probability remains low ({pct_str}) because {factors_str} actively suppress flood onset. "
                "Current catchment storage capacity is adequate to absorb prevailing precipitation."
            )
        else:
            narrative = f"Flood onset probability ({pct_str}) remains well below the early warning threshold."

    return title, narrative


def build_force_plot_data(
    base_value: float,
    output_value: float,
    contributions: List[FeatureContribution],
) -> ForcePlotData:
    """
    Package base value, directional force blocks, and final prediction for force plot rendering.
    """
    positives = [c for c in contributions if c.shap_value > 0]
    negatives = [c for c in contributions if c.shap_value < 0]

    tot_pos = float(sum(c.shap_value for c in positives))
    tot_neg = float(sum(c.shap_value for c in negatives))

    return ForcePlotData(
        base_value=round(base_value, 4),
        output_value=round(output_value, 4),
        total_positive_force=round(tot_pos, 4),
        total_negative_force=round(tot_neg, 4),
        positive_features=positives[:8],  # Top 8 positive pushes
        negative_features=negatives[:8],  # Top 8 negative pushes
        svg_markup=None,
    )
