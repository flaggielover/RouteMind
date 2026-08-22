from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field, replace
from math import isfinite
from typing import Protocol

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import GeoPoint


@dataclass(frozen=True, slots=True)
class DynamicTravelContext:
    """Deterministic inputs that can change a travel estimate without I/O."""

    simulated_time_seconds: float = 0.0
    traffic_multiplier: float = 1.0
    incident_delay_seconds: float = 0.0
    traffic_context: str = "baseline"
    incident_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isfinite(self.simulated_time_seconds) or self.simulated_time_seconds < 0:
            raise ValueError("simulated time must be finite and non-negative")
        if not isfinite(self.traffic_multiplier) or self.traffic_multiplier <= 0:
            raise ValueError("traffic multiplier must be finite and positive")
        if not isfinite(self.incident_delay_seconds) or self.incident_delay_seconds < 0:
            raise ValueError("incident delay must be finite and non-negative")
        if not self.traffic_context.strip():
            raise ValueError("traffic context must not be blank")
        if any(not incident_id.strip() for incident_id in self.incident_ids):
            raise ValueError("incident ids must not be blank")
        object.__setattr__(self, "incident_ids", tuple(sorted(set(self.incident_ids))))

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "simulated_time_seconds": self.simulated_time_seconds,
            "traffic_multiplier": self.traffic_multiplier,
            "traffic_context": self.traffic_context,
            "incident_delay_seconds": self.incident_delay_seconds,
            "incident_ids": self.incident_ids,
        }

    def with_incident(self, incident_id: str, delay_seconds: float) -> DynamicTravelContext:
        """Return a reproducible context with one incident update applied."""
        if not incident_id.strip():
            raise ValueError("incident id must not be blank")
        if not isfinite(delay_seconds) or delay_seconds < 0:
            raise ValueError("incident delay must be finite and non-negative")
        return replace(
            self,
            incident_delay_seconds=self.incident_delay_seconds + delay_seconds,
            incident_ids=(*self.incident_ids, incident_id),
        )


@dataclass(frozen=True, slots=True)
class TravelTime:
    seconds: float
    provider: str
    fallback_used: bool = False
    context: DynamicTravelContext = field(default_factory=DynamicTravelContext)

    def __post_init__(self) -> None:
        if not isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("travel time seconds must be finite and non-negative")
        if not self.provider.strip():
            raise ValueError("travel provider must not be blank")

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "fallback_used": self.fallback_used,
            **self.context.metadata,
        }


@dataclass(frozen=True, slots=True)
class TravelTimeMatrix:
    values: tuple[tuple[TravelTime, ...], ...]
    provider: str
    context: DynamicTravelContext = field(default_factory=DynamicTravelContext)
    fallback_used: bool = False

    def __post_init__(self) -> None:
        width = len(self.values[0]) if self.values else 0
        if any(len(row) != width for row in self.values):
            raise ValueError("travel time matrix must be rectangular")
        if not self.provider.strip():
            raise ValueError("travel provider must not be blank")

    @property
    def metadata(self) -> dict[str, object]:
        width = len(self.values[0]) if self.values else 0
        return {
            "provider": self.provider,
            "fallback_used": self.fallback_used,
            "rows": len(self.values),
            "columns": width,
            **self.context.metadata,
        }


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

    def estimate(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime:
        effective_context = context or DynamicTravelContext()
        distance = great_circle_distance_kilometres(
            origin.latitude, origin.longitude, destination.latitude, destination.longitude
        )
        base_seconds = distance / self.speed_kilometres_per_hour * 3600
        seconds = (
            base_seconds * effective_context.traffic_multiplier
            + effective_context.incident_delay_seconds
        )
        return TravelTime(seconds, self.name, context=effective_context)

    def matrix(
        self,
        origins: Sequence[GeoPoint],
        destinations: Sequence[GeoPoint],
        context: DynamicTravelContext | None = None,
    ) -> TravelTimeMatrix:
        values = tuple(
            tuple(self.estimate(origin, destination, context) for destination in destinations)
            for origin in origins
        )
        effective_context = context or DynamicTravelContext()
        return TravelTimeMatrix(values, self.name, effective_context)


def _invoke_with_context(
    operation: Callable[..., TravelTime | TravelTimeMatrix],
    args: tuple[object, ...],
    context: DynamicTravelContext | None,
) -> TravelTime | TravelTimeMatrix:
    if context is None:
        return operation(*args)
    try:
        return operation(*args, context=context)
    except TypeError:
        # Keep older provider implementations usable while they migrate.
        return operation(*args)


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
        self,
        operation: Callable[..., TravelTime | TravelTimeMatrix],
        *args: object,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime | TravelTimeMatrix:
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(_invoke_with_context, operation, args, context)
            return future.result(timeout=self.timeout_seconds)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def estimate(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime:
        try:
            result = self._call_with_timeout(
                self.primary.estimate, origin, destination, context=context
            )
            if not isinstance(result, TravelTime):
                raise TypeError("primary provider returned an invalid point result")
            return result
        except (Exception, TimeoutError):
            result = _invoke_with_context(self.fallback.estimate, (origin, destination), context)
            if not isinstance(result, TravelTime):
                raise TypeError("fallback provider returned an invalid point result") from None
            return TravelTime(
                result.seconds,
                result.provider,
                fallback_used=True,
                context=result.context,
            )

    def matrix(
        self,
        origins: Sequence[GeoPoint],
        destinations: Sequence[GeoPoint],
        context: DynamicTravelContext | None = None,
    ) -> TravelTimeMatrix:
        try:
            result = self._call_with_timeout(
                self.primary.matrix, origins, destinations, context=context
            )
            if not isinstance(result, TravelTimeMatrix):
                raise TypeError("primary provider returned an invalid matrix result")
            return result
        except (Exception, TimeoutError):
            raw_result = _invoke_with_context(
                self.fallback.matrix, (origins, destinations), context
            )
            if not isinstance(raw_result, TravelTimeMatrix):
                raise TypeError("fallback provider returned an invalid matrix result") from None
            result = raw_result
            values = tuple(
                tuple(
                    TravelTime(
                        item.seconds,
                        item.provider,
                        fallback_used=True,
                        context=item.context,
                    )
                    for item in row
                )
                for row in result.values
            )
            return TravelTimeMatrix(
                values,
                result.provider,
                result.context,
                fallback_used=True,
            )
