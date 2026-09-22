"""
PRAVAH Flood Propagation — Rainfall Hyetograph Service.
Models storm hyetographs, cumulative temporal precipitation fractions,
and effective excess rainfall.
"""

import math


class RainfallService:
    """
    Computes temporal rainfall distribution fractions across storm durations.
    """

    def get_cumulative_fraction(
        self,
        elapsed_hours: float,
        storm_duration_hours: float,
        distribution_type: str = "convective_core"
    ) -> float:
        """
        Calculate cumulative precipitation fraction (0.0 to 1.0) at elapsed time t.
        Uses standard SCS Type-II / synthetic convective front profiles.
        """
        if elapsed_hours <= 0.0:
            return 0.0
        if elapsed_hours >= storm_duration_hours:
            return 1.0

        fraction = elapsed_hours / storm_duration_hours

        if distribution_type == "uniform":
            return fraction
        elif distribution_type == "orographic_crest":
            # Steady mountain precipitation with late peak
            return math.sin(fraction * (math.pi / 2.0))
        else:
            # Convective core (burst in middle of storm)
            # S-curve with steep middle
            return 1.0 / (1.0 + math.exp(-8.0 * (fraction - 0.45)))
