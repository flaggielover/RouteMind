from __future__ import annotations

import pytest

from routemind_compute.application.motion import (
    CourierMotionEngine,
    CourierRoute,
    MotionStop,
)
from routemind_compute.application.travel import TravelTime
from routemind_compute.domain.dispatch import GeoPoint


class FixedTravelProvider:
    name = "fixed"

    def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime:
        return TravelTime(10, self.name)


def route() -> CourierRoute:
    return CourierRoute(
        "route-1",
        "courier-1",
        GeoPoint(0, 0),
        (
            MotionStop("pickup-1", GeoPoint(0, 1), "pickup", 5),
            MotionStop("delivery-1", GeoPoint(0, 2), "delivery", 3),
        ),
    )


def test_motion_advances_deterministically_and_projects_redis_geo() -> None:
    engine = CourierMotionEngine(FixedTravelProvider())  # type: ignore[arg-type]
    start = engine.advance(route(), 0)
    moving = engine.advance(route(), 5, start.state)
    arrival = engine.advance(route(), 10, moving.state)
    service = engine.advance(route(), 12, arrival.state)

    assert [event.event_type for event in start.events] == ["route_started"]
    assert moving.state.status == "en_route"
    assert moving.state.location == GeoPoint(0, 0.5)
    assert [event.event_type for event in arrival.events] == [
        "courier_arrived",
        "pickup_started",
    ]
    assert service.state.status == "servicing"
    assert service.state.active_stop_id == "pickup-1"
    assert service.redis_geo_members == ((1.0, 0.0, "courier-1"),)


def test_motion_emits_service_delivery_and_completion_events() -> None:
    engine = CourierMotionEngine(FixedTravelProvider())  # type: ignore[arg-type]
    snapshot = engine.advance(route(), 30)

    assert [event.event_type for event in snapshot.events] == [
        "route_started",
        "courier_arrived",
        "pickup_started",
        "pickup_completed",
        "courier_arrived",
        "delivery_started",
        "delivery_completed",
        "route_completed",
    ]
    assert snapshot.state.status == "available"
    assert snapshot.state.completed_stop_ids == ("pickup-1", "delivery-1")
    assert snapshot.state.location == GeoPoint(0, 2)
    assert len(snapshot.replay_digest) == 64


def test_motion_replay_and_incremental_events_are_stable() -> None:
    engine = CourierMotionEngine(FixedTravelProvider())  # type: ignore[arg-type]
    first = engine.advance(route(), 30)
    second = engine.advance(route(), 30)
    resumed = engine.advance(route(), 30, engine.advance(route(), 10).state)

    assert first == second
    assert resumed.events == first.events[3:]
    assert resumed.replay_digest


def test_motion_validates_state_time_and_route_contracts() -> None:
    engine = CourierMotionEngine(FixedTravelProvider())  # type: ignore[arg-type]
    snapshot = engine.advance(route(), 10)
    with pytest.raises(ValueError, match="backwards"):
        engine.advance(route(), 9, snapshot.state)
    wrong_route = CourierRoute("other", "courier-1", GeoPoint(0, 0), ())
    with pytest.raises(ValueError, match="belong"):
        engine.advance(wrong_route, 1, snapshot.state)
    with pytest.raises(ValueError, match="stop count"):
        CourierRoute(
            "too-many",
            "courier",
            GeoPoint(0, 0),
            tuple(MotionStop(str(index), GeoPoint(0, 0)) for index in range(33)),
        )
    with pytest.raises(ValueError, match="kind"):
        MotionStop("bad", GeoPoint(0, 0), "other")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="service"):
        MotionStop("bad", GeoPoint(0, 0), service_seconds=-1)
