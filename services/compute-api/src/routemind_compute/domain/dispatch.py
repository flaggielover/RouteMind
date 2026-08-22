from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

CourierState = Literal["available", "on_route", "offline", "paused"]


def _is_finite(value: float) -> bool:
    return value == value and abs(value) != float("inf")


@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")


@dataclass(frozen=True, slots=True)
class TimeWindow:
    start_seconds: float
    end_seconds: float

    def __post_init__(self) -> None:
        if not _is_finite(self.start_seconds) or not _is_finite(self.end_seconds):
            raise ValueError("time window bounds must be finite")
        if self.start_seconds < 0 or self.end_seconds < self.start_seconds:
            raise ValueError("time window must be ordered and non-negative")


@dataclass(frozen=True, slots=True)
class CourierCandidate:
    courier_id: str
    location: GeoPoint
    capacity_units: float = 1.0
    current_load_units: float = 0.0
    available_from_seconds: float = 0.0
    available_until_seconds: float | None = None
    state: CourierState = "available"
    service_risk: float = 0.0
    estimated_travel_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.courier_id.strip():
            raise ValueError("courier_id must not be blank")
        if not _is_finite(self.capacity_units) or self.capacity_units < 0:
            raise ValueError("capacity_units must be finite and non-negative")
        if not _is_finite(self.current_load_units) or self.current_load_units < 0:
            raise ValueError("current_load_units must be finite and non-negative")
        if self.current_load_units > self.capacity_units:
            raise ValueError("current_load_units cannot exceed capacity_units")
        if not _is_finite(self.available_from_seconds) or self.available_from_seconds < 0:
            raise ValueError("available_from_seconds must be finite and non-negative")
        if self.available_until_seconds is not None and (
            not _is_finite(self.available_until_seconds)
            or self.available_until_seconds < self.available_from_seconds
        ):
            raise ValueError("available_until_seconds must be ordered and finite")
        if self.state not in {"available", "on_route", "offline", "paused"}:
            raise ValueError("state must be a supported courier state")
        if not _is_finite(self.service_risk) or not 0 <= self.service_risk <= 1:
            raise ValueError("service_risk must be between 0 and 1")
        if not _is_finite(self.estimated_travel_seconds) or self.estimated_travel_seconds < 0:
            raise ValueError("estimated_travel_seconds must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class DispatchProblem:
    request_id: str
    pickup: GeoPoint
    candidates: tuple[CourierCandidate, ...]
    demand_units: float = 1.0
    pickup_ready_at_seconds: float = 0.0
    service_seconds: float = 0.0
    delivery_window: TimeWindow | None = None
    max_service_risk: float = 1.0

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")
        candidate_ids = [candidate.courier_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate courier identifiers must be unique")
        if not _is_finite(self.demand_units) or self.demand_units <= 0:
            raise ValueError("demand_units must be finite and positive")
        if not _is_finite(self.pickup_ready_at_seconds) or self.pickup_ready_at_seconds < 0:
            raise ValueError("pickup_ready_at_seconds must be finite and non-negative")
        if not _is_finite(self.service_seconds) or self.service_seconds < 0:
            raise ValueError("service_seconds must be finite and non-negative")
        if not _is_finite(self.max_service_risk) or not 0 <= self.max_service_risk <= 1:
            raise ValueError("max_service_risk must be between 0 and 1")

    def candidate_rejection_reasons(self, candidate: CourierCandidate) -> tuple[str, ...]:
        """Return stable, user-safe reasons why one courier cannot serve this demand."""
        reasons: list[str] = []
        if candidate.state != "available":
            reasons.append(f"courier_state={candidate.state}")
        if candidate.capacity_units - candidate.current_load_units < self.demand_units:
            reasons.append(
                "capacity_insufficient="
                f"{candidate.capacity_units - candidate.current_load_units:.3f}"
            )
        if candidate.service_risk > self.max_service_risk:
            reasons.append(f"service_risk_exceeded={candidate.service_risk:.3f}")
        service_start = max(self.pickup_ready_at_seconds, candidate.available_from_seconds)
        delivery_at = service_start + candidate.estimated_travel_seconds + self.service_seconds
        if self.delivery_window is not None:
            delivery_at = max(delivery_at, self.delivery_window.start_seconds)
            if delivery_at > self.delivery_window.end_seconds:
                reasons.append(f"delivery_window_missed={self.delivery_window.end_seconds:.3f}")
        if (
            candidate.available_until_seconds is not None
            and delivery_at > candidate.available_until_seconds
        ):
            reasons.append(f"courier_unavailable_until={candidate.available_until_seconds:.3f}")
        return tuple(reasons)

    def eligible_candidates(self) -> tuple[CourierCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.candidates
            if not self.candidate_rejection_reasons(candidate)
        )

    def infeasibility_reasons(self) -> tuple[str, ...]:
        if not self.candidates:
            return ("no courier candidates",)
        reasons = tuple(
            f"{candidate.courier_id}:{reason}"
            for candidate in self.candidates
            for reason in self.candidate_rejection_reasons(candidate)
        )
        return reasons or ("no eligible courier",)


@dataclass(frozen=True, slots=True)
class DispatchDecision:
    request_id: str
    strategy: str
    courier_id: str | None
    score: float | None
    rationale: tuple[str, ...] = ()
    strategy_version: str = "1.0.0"
    latency_millis: float = 0.0
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")
        if not self.strategy.strip():
            raise ValueError("strategy must not be blank")
        if not self.strategy_version.strip():
            raise ValueError("strategy_version must not be blank")
        if not (0 <= self.latency_millis < 1e308):
            raise ValueError("latency_millis must be finite and non-negative")
        if self.courier_id is None and self.score is not None:
            raise ValueError("an unassigned decision cannot have a score")


@runtime_checkable
class DispatchStrategy(Protocol):
    @property
    def name(self) -> str: ...

    def solve(self, problem: DispatchProblem) -> DispatchDecision: ...
