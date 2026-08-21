from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import GeoPoint


@dataclass(frozen=True, slots=True)
class TravelTime:
    seconds: float
    provider: str
    fallback_used: bool = False

    def __post_init__(self) -> None:
        if not isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("travel time seconds must be finite and non-negative")
        if not self.provider.strip():
            raise ValueError("travel provider must not be blank")


@dataclass(frozen=True, slots=True)
class TravelTimeMatrix:
    values: tuple[tuple[TravelTime, ...], ...]
    provider: str

    def __post_init__(self) -> None:
        width = len(self.values[0]) if self.values else 0
        if any(len(row) != width for row in self.values):
            raise ValueError("travel time matrix must be rectangular")
        if not self.provider.strip():
            raise ValueError("travel provider must not be blank")


class TravelTimeProvider(Protocol):
    @property
    def name(self) -> str: ...

    def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime: ...

    def matrix(
        self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]
    ) -> TravelTimeMatrix: ...


class DeterministicLocalTravelProvider:
    name = "deterministic-local"

    def __init__(self, speed_kilometres_per_hour: float = 30.0) -> None:
        if not isfinite(speed_kilometres_per_hour) or speed_kilometres_per_hour <= 0:
            raise ValueError("speed must be finite and positive")
        self.speed_kilometres_per_hour = speed_kilometres_per_hour

    def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime:
        distance = great_circle_distance_kilometres(
            origin.latitude, origin.longitude, destination.latitude, destination.longitude
        )
        return TravelTime(distance / self.speed_kilometres_per_hour * 3600, self.name)

    def matrix(
        self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]
    ) -> TravelTimeMatrix:
        values = tuple(
            tuple(self.estimate(origin, destination) for destination in destinations)
            for origin in origins
        )
        return TravelTimeMatrix(values, self.name)


class FallbackTravelTimeProvider:
    def __init__(
        self,
        primary: TravelTimeProvider,
        fallback: TravelTimeProvider,
        timeout_seconds: float = 1.0,
    ) -> None:
        if timeout_seconds <= 0 or not isfinite(timeout_seconds):
            raise ValueError("timeout must be finite and positive")
        self.primary = primary
        self.fallback = fallback
        self.timeout_seconds = timeout_seconds
        self.name = f"fallback({primary.name}->{fallback.name})"

    def _call_with_timeout(
        self, operation: Callable[..., TravelTime | TravelTimeMatrix], *args: object
    ) -> TravelTime | TravelTimeMatrix:
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(operation, *args)
            return future.result(timeout=self.timeout_seconds)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime:
        try:
            result = self._call_with_timeout(self.primary.estimate, origin, destination)
            if not isinstance(result, TravelTime):
                raise TypeError("primary provider returned an invalid point result")
            return result
        except (Exception, TimeoutError):
            result = self.fallback.estimate(origin, destination)
            return TravelTime(result.seconds, result.provider, fallback_used=True)

    def matrix(
        self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]
    ) -> TravelTimeMatrix:
        try:
            result = self._call_with_timeout(self.primary.matrix, origins, destinations)
            if not isinstance(result, TravelTimeMatrix):
                raise TypeError("primary provider returned an invalid matrix result")
            return result
        except (Exception, TimeoutError):
            result = self.fallback.matrix(origins, destinations)
            values = tuple(
                tuple(TravelTime(item.seconds, item.provider, fallback_used=True) for item in row)
                for row in result.values
            )
            return TravelTimeMatrix(values, result.provider)
