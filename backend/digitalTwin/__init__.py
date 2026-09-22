"""
PRAVAH Digital Twin — Backward Compatibility Proxy.
Re-exports DigitalTwinManager and simulation components from src.digital_twin.
"""

from src.digital_twin import (
    DigitalTwinManager,
    SimulationEngine,
    Watershed,
    WatershedProperties,
    TerrainModelOutput,
    RiverBasinSummary,
    SimulationRequest,
    SimulationResult,
    AntecedentMoistureCondition,
    SimulationMode,
    AccumulationSeverity,
)

__all__ = [
    "DigitalTwinManager",
    "SimulationEngine",
    "Watershed",
    "WatershedProperties",
    "TerrainModelOutput",
    "RiverBasinSummary",
    "SimulationRequest",
    "SimulationResult",
    "AntecedentMoistureCondition",
    "SimulationMode",
    "AccumulationSeverity",
]
