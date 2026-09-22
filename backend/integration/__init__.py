"""
PRAVAH Platform Integration — Backward Compatibility Proxy.
Re-exports PlatformOrchestrator and routes from src.integration.
"""

from src.integration import (
    PlatformOrchestrator,
    get_platform_orchestrator,
    integration_router,
)

__all__ = [
    "PlatformOrchestrator",
    "get_platform_orchestrator",
    "integration_router",
]
