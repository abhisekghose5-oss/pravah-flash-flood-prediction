"""
PRAVAH Flood Propagation — Impact Assessment Engine.
Integrates demographic exposure and infrastructure risk at each simulation time step.
"""

from typing import Optional

from src.simulation.models.impact import (
    TimeStepImpactSummary,
    InfrastructureImpactSummary,
    PopulationExposure,
)
from src.simulation.services.population_service import PopulationService
from src.simulation.services.infrastructure_service import InfrastructureService


class ImpactEngine:
    """
    Coordinates population and infrastructure impact evaluations across advancing flood extents.
    """

    def __init__(
        self,
        population_service: Optional[PopulationService] = None,
        infrastructure_service: Optional[InfrastructureService] = None
    ):
        self.population_service = population_service or PopulationService()
        self.infrastructure_service = infrastructure_service or InfrastructureService()

    def evaluate_step_impact(
        self,
        time_hours: float,
        time_label: str,
        catchment_id: str,
        center_lat: float,
        center_lon: float,
        flooded_area_km2: float,
        flood_radius_km: float,
        peak_depth_m: float
    ) -> TimeStepImpactSummary:
        """
        Produce consolidated impact report at a discrete time step.
        """
        # Demographic exposure
        pop_exposure = self.population_service.calculate_exposure(
            catchment_id=catchment_id,
            inundated_area_km2=flooded_area_km2,
            peak_depth_m=peak_depth_m,
        )

        # Lifeline infrastructure impact
        infra_summary = self.infrastructure_service.evaluate_impact(
            center_lat=center_lat,
            center_lon=center_lon,
            flood_radius_km=flood_radius_km,
            peak_depth_m=peak_depth_m,
            catchment_id=catchment_id,
        )

        return TimeStepImpactSummary(
            time_step_hours=time_hours,
            time_label=time_label,
            population=pop_exposure,
            infrastructure=infra_summary,
        )
