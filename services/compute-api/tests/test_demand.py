from __future__ import annotations

import pytest

from routemind_compute.application.demand import (
    DemandArrivalGenerator,
    DemandArrivalProfile,
)
from routemind_compute.domain.dispatch import GeoPoint


def profiles() -> tuple[DemandArrivalProfile, ...]:
    return (
        DemandArrivalProfile(
            "breakfast",
            rate_per_hour=60,
            start_tick=0,
            end_tick=2,
            location=GeoPoint(31.23, 121.47),
            zone="north",
            merchant_id="merchant-1",
            order_profile="meal",
            burst_size=2,
        ),
        DemandArrivalProfile(
            "late",
            rate_per_hour=0,
            start_tick=0,
            end_tick=2,
            location=GeoPoint(31.24, 121.46),
        ),
    )


def test_demand_generation_is_seeded_sorted_and_replayable() -> None:
    generator = DemandArrivalGenerator(60)
    first = generator.generate(profiles(), 7)
    second = generator.generate(profiles(), 7)

    assert first == second
    assert len(first.arrivals) == 6
    assert [arrival.request_id for arrival in first.arrivals] == sorted(
        arrival.request_id for arrival in first.arrivals
    )
    assert {arrival.zone for arrival in first.arrivals} == {"north"}
    assert {arrival.order_profile for arrival in first.arrivals} == {"meal"}
    assert len(first.replay_digest) == 64
    assert generator.generate(profiles(), 8).replay_digest != first.replay_digest


def test_demand_profiles_validate_explicit_inputs() -> None:
    with pytest.raises(ValueError, match="profile id"):
        DemandArrivalProfile(" ", 1, 0, 1, GeoPoint(0, 0))
    with pytest.raises(ValueError, match="rate"):
        DemandArrivalProfile("p", -1, 0, 1, GeoPoint(0, 0))
    with pytest.raises(ValueError, match="ticks"):
        DemandArrivalProfile("p", 1, 2, 1, GeoPoint(0, 0))
    with pytest.raises(ValueError, match="order profile"):
        DemandArrivalProfile("p", 1, 0, 1, GeoPoint(0, 0), order_profile=" ")
    with pytest.raises(ValueError, match="burst"):
        DemandArrivalProfile("p", 1, 0, 1, GeoPoint(0, 0), burst_size=0)
    with pytest.raises(ValueError, match="profile identifiers"):
        DemandArrivalGenerator().generate((profiles()[0], profiles()[0]), 1)
