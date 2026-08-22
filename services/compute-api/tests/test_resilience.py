from __future__ import annotations

from collections.abc import Sequence

from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    FallbackTravelTimeProvider,
)
from routemind_compute.domain.dispatch import GeoPoint

ORIGIN = GeoPoint(31.2304, 121.4737)
DESTINATION = GeoPoint(31.22, 121.48)


class FailingTravelProvider:
    name = "injected-timeout"

    def estimate(self, origin: GeoPoint, destination: GeoPoint):  # type: ignore[no-untyped-def]
        raise TimeoutError("injected travel provider timeout")

    def matrix(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]):  # type: ignore[no-untyped-def]
        raise RuntimeError("injected travel provider failure")


def test_provider_timeout_uses_bounded_local_fallback() -> None:
    provider = FallbackTravelTimeProvider(
        FailingTravelProvider(), DeterministicLocalTravelProvider(), timeout_seconds=0.1
    )

    result = provider.estimate(ORIGIN, DESTINATION)

    assert result.provider == "deterministic-local"
    assert result.fallback_used is True


def test_provider_failure_marks_every_matrix_cell_as_fallback() -> None:
    provider = FallbackTravelTimeProvider(
        FailingTravelProvider(), DeterministicLocalTravelProvider(), timeout_seconds=0.1
    )

    result = provider.matrix((ORIGIN,), (DESTINATION, ORIGIN))

    assert result.provider == "deterministic-local"
    assert all(item.fallback_used for row in result.values for item in row)
