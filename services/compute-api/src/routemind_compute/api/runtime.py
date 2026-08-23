from __future__ import annotations

from dataclasses import dataclass

from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    FallbackTravelTimeProvider,
)
from routemind_compute.application.twin_control import TwinControlService
from routemind_compute.application.what_if import WhatIfRunner


@dataclass(frozen=True)
class ComputeRuntime:
    """Composition root for stateful compute collaborators used by API routes."""

    registry: StrategyRegistry
    travel_provider: FallbackTravelTimeProvider
    twin_control: TwinControlService
    what_if: WhatIfRunner


def create_runtime() -> ComputeRuntime:
    registry = default_registry()
    travel_provider = FallbackTravelTimeProvider(
        DeterministicLocalTravelProvider(), DeterministicLocalTravelProvider()
    )
    return ComputeRuntime(
        registry=registry,
        travel_provider=travel_provider,
        twin_control=TwinControlService(registry, travel_provider),
        what_if=WhatIfRunner(registry, travel_provider),
    )
