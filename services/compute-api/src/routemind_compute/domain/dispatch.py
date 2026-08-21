from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


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
class CourierCandidate:
    courier_id: str
    location: GeoPoint

    def __post_init__(self) -> None:
        if not self.courier_id.strip():
            raise ValueError("courier_id must not be blank")


@dataclass(frozen=True, slots=True)
class DispatchProblem:
    request_id: str
    pickup: GeoPoint
    candidates: tuple[CourierCandidate, ...]

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")
        candidate_ids = [candidate.courier_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate courier identifiers must be unique")


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
