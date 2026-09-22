"""
PRAVAH Platform Integration & Orchestration Package.
Consolidates all 9 subsystems: River Gauges, SMS, WhatsApp, Telegram, IVRS,
Evacuation Planning, Explainable AI, Digital Twin, and Flood Propagation Simulator.
"""

from src.integration.platform_orchestrator import (
    PlatformOrchestrator,
    get_platform_orchestrator,
)
from src.integration.routes.integration_routes import router as integration_router

__all__ = [
    "PlatformOrchestrator",
    "get_platform_orchestrator",
    "integration_router",
]
