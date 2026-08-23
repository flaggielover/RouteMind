from __future__ import annotations

from dataclasses import dataclass

from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.application.tracing import TracingRuntime
from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    FallbackTravelTimeProvider,
    TracedTravelTimeProvider,
    TravelTimeProvider,
)
from routemind_compute.application.twin_control import TwinControlService
from routemind_compute.application.what_if import WhatIfRunner


@dataclass(frozen=True)
class ComputeRuntime:
    """Composition root for stateful compute collaborators used by API routes."""

    registry: StrategyRegistry
    travel_provider: TravelTimeProvider
    tracing: TracingRuntime
    twin_control: TwinControlService
    what_if: WhatIfRunner


def create_runtime(tracing_runtime: TracingRuntime | None = None) -> ComputeRuntime:
    tracing = tracing_runtime or TracingRuntime()
    registry = default_registry(tracer=tracing.tracer)
    travel_provider = TracedTravelTimeProvider(
        FallbackTravelTimeProvider(
            DeterministicLocalTravelProvider(), DeterministicLocalTravelProvider()
        ),
        tracer=tracing.tracer,
    )
    return ComputeRuntime(
        registry=registry,
        travel_provider=travel_provider,
        tracing=tracing,
        twin_control=TwinControlService(registry, travel_provider),
        what_if=WhatIfRunner(registry, travel_provider),
    )
