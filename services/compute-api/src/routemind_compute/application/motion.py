from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from routemind_compute.application.travel import TravelTimeProvider
from routemind_compute.domain.dispatch import GeoPoint

MotionStopKind = Literal["pickup", "delivery"]
MotionStatus = Literal["idle", "en_route", "servicing", "available"]


@dataclass(frozen=True, slots=True)
class MotionStop:
    stop_id: str
    location: GeoPoint
    kind: MotionStopKind = "pickup"
    service_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.stop_id.strip():
            raise ValueError("motion stop id must not be blank")
        if self.kind not in {"pickup", "delivery"}:
            raise ValueError("motion stop kind is not supported")
        if not isfinite(self.service_seconds) or self.service_seconds < 0:
            raise ValueError("motion service seconds must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class CourierRoute:
    route_id: str
    courier_id: str
    start_location: GeoPoint
    stops: tuple[MotionStop, ...]
    started_at_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.route_id.strip() or not self.courier_id.strip():
            raise ValueError("motion route identity must not be blank")
        if len(self.stops) > 32:
            raise ValueError("motion route stop count must not exceed 32")
        stop_ids = tuple(stop.stop_id for stop in self.stops)
        if len(stop_ids) != len(set(stop_ids)):
            raise ValueError("motion stop identifiers must be unique")
        if not isfinite(self.started_at_seconds) or self.started_at_seconds < 0:
            raise ValueError("motion route start time must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class MotionEvent:
    event_id: str
    event_type: str
    observed_at_seconds: float
    route_id: str
    courier_id: str
    location: GeoPoint
    stop_id: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.event_type.strip():
            raise ValueError("motion event identity must not be blank")
        if not isfinite(self.observed_at_seconds) or self.observed_at_seconds < 0:
            raise ValueError("motion event time must be finite and non-negative")
        if not self.route_id.strip() or not self.courier_id.strip():
            raise ValueError("motion event route identity must not be blank")


@dataclass(frozen=True, slots=True)
class CourierMotionState:
    route_id: str
    courier_id: str
    observed_at_seconds: float
    location: GeoPoint
    status: MotionStatus
    active_stop_id: str | None
    completed_stop_ids: tuple[str, ...]
    emitted_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CourierLocationProjection:
    courier_id: str
    location: GeoPoint
    observed_at_seconds: float
    route_id: str
    status: MotionStatus

    @property
    def redis_geo_member(self) -> tuple[float, float, str]:
        """Return Redis GEOADD ordering: longitude, latitude, member."""
        return (self.location.longitude, self.location.latitude, self.courier_id)


@dataclass(frozen=True, slots=True)
class MotionSnapshot:
    route_id: str
    courier_id: str
    state: CourierMotionState
    events: tuple[MotionEvent, ...]
    projection: CourierLocationProjection

    @property
    def redis_geo_members(self) -> tuple[tuple[float, float, str], ...]:
        return (self.projection.redis_geo_member,)

    @property
    def replay_digest(self) -> str:
        payload = {
            "route_id": self.route_id,
            "courier_id": self.courier_id,
            "state": {
                "observed_at_seconds": self.state.observed_at_seconds,
                "location": (self.state.location.latitude, self.state.location.longitude),
                "status": self.state.status,
                "active_stop_id": self.state.active_stop_id,
                "completed_stop_ids": self.state.completed_stop_ids,
                "emitted_event_ids": self.state.emitted_event_ids,
            },
            "events": [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "observed_at_seconds": event.observed_at_seconds,
                    "stop_id": event.stop_id,
                }
                for event in self.events
            ],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class CourierMotionEngine:
    """Advance an immutable courier route snapshot using simulated time only."""

    version = "1.0.0"

    def __init__(self, travel_provider: TravelTimeProvider) -> None:
        self.travel_provider = travel_provider

    def advance(
        self,
        route: CourierRoute,
        to_seconds: float,
        state: CourierMotionState | None = None,
    ) -> MotionSnapshot:
        current = state or CourierMotionState(
            route.route_id,
            route.courier_id,
            route.started_at_seconds,
            route.start_location,
            "idle",
            None,
            (),
            (),
        )
        if current.route_id != route.route_id or current.courier_id != route.courier_id:
            raise ValueError("motion state does not belong to route")
        if not isfinite(to_seconds) or to_seconds < current.observed_at_seconds:
            raise ValueError("motion time cannot move backwards")
        timeline = self._timeline(route)
        emitted = set(current.emitted_event_ids)
        events = tuple(
            event
            for event in timeline
            if event.event_id not in emitted
            and current.observed_at_seconds - 1e-9 <= event.observed_at_seconds <= to_seconds + 1e-9
        )
        emitted.update(event.event_id for event in events)
        location, status, active_stop_id, completed = self._position_at(route, to_seconds)
        next_state = CourierMotionState(
            route.route_id,
            route.courier_id,
            to_seconds,
            location,
            status,
            active_stop_id,
            completed,
            tuple(event.event_id for event in timeline if event.event_id in emitted),
        )
        projection = CourierLocationProjection(
            route.courier_id,
            location,
            to_seconds,
            route.route_id,
            status,
        )
        return MotionSnapshot(route.route_id, route.courier_id, next_state, events, projection)

    def _timeline(self, route: CourierRoute) -> tuple[MotionEvent, ...]:
        events: list[MotionEvent] = [
            MotionEvent(
                f"{route.route_id}:started",
                "route_started",
                route.started_at_seconds,
                route.route_id,
                route.courier_id,
                route.start_location,
            )
        ]
        clock = route.started_at_seconds
        current = route.start_location
        for stop in route.stops:
            travel = self.travel_provider.estimate(current, stop.location).seconds
            clock += travel
            events.append(
                MotionEvent(
                    f"{route.route_id}:arrival:{stop.stop_id}",
                    "courier_arrived",
                    clock,
                    route.route_id,
                    route.courier_id,
                    stop.location,
                    stop.stop_id,
                )
            )
            events.append(
                MotionEvent(
                    f"{route.route_id}:{stop.kind}_started:{stop.stop_id}",
                    f"{stop.kind}_started",
                    clock,
                    route.route_id,
                    route.courier_id,
                    stop.location,
                    stop.stop_id,
                )
            )
            clock += stop.service_seconds
            events.append(
                MotionEvent(
                    f"{route.route_id}:{stop.kind}_completed:{stop.stop_id}",
                    f"{stop.kind}_completed",
                    clock,
                    route.route_id,
                    route.courier_id,
                    stop.location,
                    stop.stop_id,
                )
            )
            current = stop.location
        events.append(
            MotionEvent(
                f"{route.route_id}:completed",
                "route_completed",
                clock,
                route.route_id,
                route.courier_id,
                current,
            )
        )
        return tuple(events)

    def _position_at(
        self, route: CourierRoute, observed_at_seconds: float
    ) -> tuple[GeoPoint, MotionStatus, str | None, tuple[str, ...]]:
        if observed_at_seconds < route.started_at_seconds:
            return route.start_location, "idle", None, ()
        clock = route.started_at_seconds
        current = route.start_location
        completed: list[str] = []
        for stop in route.stops:
            travel = self.travel_provider.estimate(current, stop.location).seconds
            arrival = clock + travel
            completion = arrival + stop.service_seconds
            if observed_at_seconds < arrival - 1e-9:
                fraction = (observed_at_seconds - clock) / travel if travel else 1.0
                location = GeoPoint(
                    current.latitude + (stop.location.latitude - current.latitude) * fraction,
                    current.longitude + (stop.location.longitude - current.longitude) * fraction,
                )
                return location, "en_route", stop.stop_id, tuple(completed)
            if observed_at_seconds < completion - 1e-9:
                return stop.location, "servicing", stop.stop_id, tuple(completed)
            completed.append(stop.stop_id)
            current = stop.location
            clock = completion
        return current, "available", None, tuple(completed)
