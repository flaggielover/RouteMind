from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from routemind_compute.application.google_routes import (
    GoogleRoutesError,
    GoogleRoutesPolicy,
    GoogleRoutesProvider,
    GoogleRoutesResponse,
)
from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.application.telemetry import TenantTelemetryAttribution
from routemind_compute.application.tracing import TracingRuntime
from routemind_compute.application.travel import (
    FallbackTravelTimeProvider,
    LocalRoutingProvider,
    TracedTravelTimeProvider,
    TravelTimeProvider,
)
from routemind_compute.application.twin_control import TwinControlService
from routemind_compute.application.what_if import WhatIfRunner


class _UnconfiguredGoogleRoutesTransport:
    """Keep ordinary runtime startup and tests strictly zero-live-call."""

    def __call__(
        self,
        *,
        operation: str,
        endpoint: str,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> GoogleRoutesResponse:
        del operation, endpoint, headers, body, timeout_seconds
        raise GoogleRoutesError("transport_unconfigured")


@dataclass(frozen=True)
class ComputeRuntime:
    """Composition root for stateful compute collaborators used by API routes."""

    registry: StrategyRegistry
    travel_provider: TravelTimeProvider
    tracing: TracingRuntime
    telemetry: TenantTelemetryAttribution
    twin_control: TwinControlService
    what_if: WhatIfRunner


def create_runtime(
    tracing_runtime: TracingRuntime | None = None,
    telemetry: TenantTelemetryAttribution | None = None,
) -> ComputeRuntime:
    tracing = tracing_runtime or TracingRuntime()
    registry = default_registry(tracer=tracing.tracer)
    google_primary = GoogleRoutesProvider(
        _UnconfiguredGoogleRoutesTransport(),
        # A transport is injected by an explicitly approved external runner;
        # the composition root never performs provider I/O by itself.
        policy=GoogleRoutesPolicy(max_retries=0, rate_limit_per_second=0),
    )
    travel_provider = TracedTravelTimeProvider(
        FallbackTravelTimeProvider(google_primary, LocalRoutingProvider()),
        tracer=tracing.tracer,
    )
    return ComputeRuntime(
        registry=registry,
        travel_provider=travel_provider,
        tracing=tracing,
        telemetry=telemetry or TenantTelemetryAttribution(),
        twin_control=TwinControlService(registry, travel_provider),
        what_if=WhatIfRunner(registry, travel_provider),
    )
