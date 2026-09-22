"""
PRAVAH Flood Propagation — Simulation Mathematical Utilities.
Provides temporal time-step intervals, sigmoidal wave propagation curves,
and depth-decay formulas.
"""

import math
from typing import List


def get_discrete_time_steps(period_hours: int) -> List[float]:
    """
    Generate realistic temporal discretization steps for a given simulation period.
    Always includes T+0h, inception steps, intermediate stages, and final horizon.
    """
    if period_hours <= 1:
        return [0.0, 0.25, 0.5, 0.75, 1.0]
    elif period_hours <= 6:
        return [0.0, 1.0, 2.0, 4.0, 6.0]
    elif period_hours <= 12:
        return [0.0, 1.0, 3.0, 6.0, 9.0, 12.0]
    elif period_hours <= 24:
        return [0.0, 1.0, 3.0, 6.0, 12.0, 18.0, 24.0]
    else:  # 48 hours
        return [0.0, 1.0, 6.0, 12.0, 24.0, 36.0, 48.0]


def propagation_fraction(t_hours: float, max_hours: float, steepness: float = 4.0) -> float:
    """
    Compute cumulative flood extent growth fraction (0.0 to 1.0) using a smooth
    S-curve (sigmoidal hydrograph wave) reflecting hydraulic wave arrival and floodplain storage.
    """
    if t_hours <= 0.0:
        return 0.0
    if t_hours >= max_hours:
        return 1.0

    # Normalized time 0 to 1
    norm_t = t_hours / max(1.0, max_hours)
    # Scaled sigmoid centered around 35% of duration (rapid onset, then attenuation)
    raw = 1.0 / (1.0 + math.exp(-steepness * (norm_t - 0.35)))
    min_val = 1.0 / (1.0 + math.exp(steepness * 0.35))
    max_val = 1.0 / (1.0 + math.exp(-steepness * 0.65))

    scaled = (raw - min_val) / max(0.01, max_val - min_val)
    return max(0.0, min(1.0, scaled))
