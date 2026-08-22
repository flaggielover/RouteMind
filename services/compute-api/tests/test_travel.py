from __future__ import annotations

import time
from collections.abc import Sequence

import pytest

from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    DynamicTravelContext,
    FallbackTravelTimeProvider,
    TravelTime,
    TravelTimeMatrix,
)
from routemind_compute.domain.dispatch import GeoPoint

ORIGIN = GeoPoint(31.2304, 121.4737)
DESTINATION = GeoPoint(31.22, 121.48)


def test_local_provider_is_deterministic_and_supports_point_and_matrix() -> None:
    provider = DeterministicLocalTravelProvider()
    point = provider.estimate(ORIGIN, DESTINATION)
    matrix = provider.matrix((ORIGIN,), (DESTINATION, ORIGIN))

    assert point.provider == "deterministic-local"
    assert point.seconds == matrix.values[0][0].seconds
    assert matrix.values[0][1].seconds == 0


def test_dynamic_context_adjusts_estimates_and_preserves_metadata() -> None:
    provider = DeterministicLocalTravelProvider()
    baseline = provider.estimate(ORIGIN, DESTINATION)
    context = DynamicTravelContext(
        simulated_time_seconds=3600,
        traffic_multiplier=1.5,
        traffic_context="peak",
        incident_ids=("incident-b", "incident-a"),
        incident_delay_seconds=30,
    )

    point = provider.estimate(ORIGIN, DESTINATION, context)
    matrix = provider.matrix((ORIGIN,), (DESTINATION,), context)

    assert point.seconds == pytest.approx(baseline.seconds * 1.5 + 30)
    assert point.context == context
    assert point.metadata["provider"] == "deterministic-local"
    assert point.metadata["traffic_context"] == "peak"
    assert point.context.incident_ids == ("incident-a", "incident-b")
    assert matrix.context == context
    assert matrix.metadata["rows"] == 1
    assert matrix.values[0][0].metadata["simulated_time_seconds"] == 3600


def test_incident_updates_are_immutable_and_validated() -> None:
    context = DynamicTravelContext(traffic_context="off-peak")
    updated = context.with_incident("road-closure", 45)

    assert context.incident_ids == ()
    assert updated.incident_ids == ("road-closure",)
    assert updated.incident_delay_seconds == 45
    with pytest.raises(ValueError, match="incident id"):
        context.with_incident(" ", 1)
    with pytest.raises(ValueError, match="incident delay"):
        context.with_incident("road-closure", -1)


def test_provider_rejects_invalid_configuration_and_matrix_shape() -> None:
    with pytest.raises(ValueError, match="speed"):
        DeterministicLocalTravelProvider(0)
    with pytest.raises(ValueError, match="traffic multiplier"):
        DynamicTravelContext(traffic_multiplier=0)
    with pytest.raises(ValueError, match="traffic context"):
        DynamicTravelContext(traffic_context=" ")
    with pytest.raises(ValueError, match="incident ids"):
        DynamicTravelContext(incident_ids=("",))
    with pytest.raises(ValueError, match="seconds"):
        TravelTime(-1, "test")
    with pytest.raises(ValueError, match="provider"):
        TravelTime(1, " ")
    with pytest.raises(ValueError, match="rectangular"):
        TravelTimeMatrix(((TravelTime(1, "test"),), ()), "test")
    with pytest.raises(ValueError, match="provider"):
        TravelTimeMatrix((), " ")
    with pytest.raises(ValueError, match="timeout"):
        FallbackTravelTimeProvider(
            DeterministicLocalTravelProvider(), DeterministicLocalTravelProvider(), 0
        )


def test_fallback_provider_handles_errors_and_timeout() -> None:
    class BrokenProvider:
        name = "broken"

        def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime:
            raise RuntimeError("down")

        def matrix(
            self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]
        ) -> TravelTimeMatrix:
            raise RuntimeError("down")

    class SlowProvider(BrokenProvider):
        def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime:
            time.sleep(0.05)
            return TravelTime(1, self.name)

    fallback = DeterministicLocalTravelProvider()
    provider = FallbackTravelTimeProvider(BrokenProvider(), fallback)
    assert provider.estimate(ORIGIN, DESTINATION).fallback_used
    assert provider.matrix((ORIGIN,), (DESTINATION,)).values[0][0].fallback_used

    timed_out = FallbackTravelTimeProvider(SlowProvider(), fallback, timeout_seconds=0.001)
    assert timed_out.estimate(ORIGIN, DESTINATION).fallback_used

    context = DynamicTravelContext(traffic_multiplier=2, incident_delay_seconds=10)
    dynamic = provider.estimate(ORIGIN, DESTINATION, context)
    assert dynamic.fallback_used
    assert dynamic.context == context

    class InvalidResultProvider(BrokenProvider):
        def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime:
            return "invalid"  # type: ignore[return-value]

        def matrix(
            self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]
        ) -> TravelTimeMatrix:
            return "invalid"  # type: ignore[return-value]

    invalid = FallbackTravelTimeProvider(InvalidResultProvider(), fallback)
    assert invalid.estimate(ORIGIN, DESTINATION).fallback_used
    assert invalid.matrix((ORIGIN,), (DESTINATION,)).values[0][0].fallback_used
