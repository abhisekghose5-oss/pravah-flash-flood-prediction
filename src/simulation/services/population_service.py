"""
PRAVAH Flood Propagation — Population Impact Service.
Calculates demographic exposure by intersecting dynamic flood extents
with catchment-level LULC population features.
"""

import csv
import logging
import os
from typing import Dict, Optional

from src.simulation.models.impact import (
    PopulationExposure,
    EvacuationUrgency,
)

logger = logging.getLogger("pravah.simulation.population")


class PopulationService:
    """
    Manages demographic datasets and estimates resident population exposure
    across advancing flood footprints.
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..")
            )
        else:
            self.base_dir = base_dir

        self.population_data: Dict[str, Dict[str, float]] = {}
        self._load_population_features()

    def _load_population_features(self) -> None:
        """Load catchment-level population metrics from CSV."""
        csv_path = os.path.join(
            self.base_dir,
            "data", "processed", "target_catchment_lulc_population_features.csv"
        )
        if not os.path.exists(csv_path):
            logger.warning("Population features CSV not found at %s", csv_path)
            return

        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    gid = row.get("GaugeID", "").strip()
                    self.population_data[gid] = {
                        "area_km2": float(row.get("catchment_area_km2") or 500.0),
                        "total_pop": float(row.get("population_total") or 100000.0),
                        "pop_density": float(row.get("population_density_per_km2") or 250.0),
                        "urban_pct": float(row.get("urban_built_up_pct") or 40.0),
                    }
                    # Also index with prefix
                    self.population_data[f"INDOFLOODS-gauge-{gid}"] = self.population_data[gid]
            logger.info("Loaded population features for %d catchments", len(self.population_data))
        except Exception as exc:
            logger.error("Failed to load population features: %s", exc)

    def calculate_exposure(
        self,
        catchment_id: str,
        inundated_area_km2: float,
        peak_depth_m: float
    ) -> PopulationExposure:
        """
        Estimate population exposed to floodwaters based on inundated area,
        catchment population density, and flood depth.
        """
        data = self.population_data.get(catchment_id)
        if not data:
            # Fallback to Mahad Savitri (gauge 602) baseline density
            data = self.population_data.get("602", {
                "pop_density": 220.0,
                "urban_pct": 55.0,
                "total_pop": 135000.0
            })

        density = data["pop_density"]
        urban_factor = 1.0 + (data["urban_pct"] / 100.0) * 0.4

        # Estimated exposed population = Inundated Area (km²) * Density * Urban Factor
        raw_exposed = inundated_area_km2 * density * urban_factor
        # Cap at total catchment population
        total_exposed = int(min(data.get("total_pop", 250000), max(0, raw_exposed)))

        # High risk population (depth > 1.5m)
        high_risk_ratio = min(0.65, max(0.15, peak_depth_m / 4.0))
        high_risk_pop = int(total_exposed * high_risk_ratio)

        # Vulnerable subsets (infants, elderly ~ 22% of exposed)
        vulnerable_pop = int(total_exposed * 0.22)

        # Evacuation urgency based on depth and count
        if peak_depth_m >= 2.5 or total_exposed >= 25000:
            urgency = EvacuationUrgency.MANDATORY
        elif peak_depth_m >= 1.2 or total_exposed >= 10000:
            urgency = EvacuationUrgency.URGENT
        elif peak_depth_m >= 0.5 or total_exposed >= 2500:
            urgency = EvacuationUrgency.ADVISORY
        else:
            urgency = EvacuationUrgency.MONITORING

        return PopulationExposure(
            estimated_population_exposed=total_exposed,
            population_density_per_km2=round(density, 1),
            high_risk_population=high_risk_pop,
            elderly_and_children_estimate=vulnerable_pop,
            evacuation_urgency=urgency,
            data_source_badge="ESTIMATED — LULC Census & Global Human Settlement Layer",
        )

    def is_loaded(self) -> bool:
        """Check if population data from CSV is loaded."""
        return len(self.population_data) > 0
