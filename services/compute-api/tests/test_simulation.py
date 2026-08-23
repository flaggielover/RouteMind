from __future__ import annotations

import pytest

from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.simulation import (
    CourierState,
    DemandEvent,
    ScenarioKernel,
    ScenarioManifest,
    TwinClock,
)
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.domain.dispatch import GeoPoint


def manifest(seed: int = 7) -> ScenarioManifest:
    return ScenarioManifest(
        "scenario-1",
        seed,
        (
            DemandEvent("request-1", GeoPoint(31.2304, 121.4737), 0),
            DemandEvent("request-2", GeoPoint(31.2305, 121.4738), 0),
        ),
        (
            CourierState("courier-1", GeoPoint(31.22, 121.48)),
            CourierState("courier-2", GeoPoint(31.24, 121.46)),
        ),
        delay_ticks=(0, 1),
        traffic_multiplier=1.2,
    )


def kernel() -> ScenarioKernel:
    return ScenarioKernel(
        StrategyRegistry((NearestStrategy(),)), DeterministicLocalTravelProvider()
    )


def test_repeated_runs_are_deterministic_and_replayable() -> None:
    first = kernel().run(manifest())
    second = kernel().run(manifest())

    assert first == second
    assert len(first.decisions) == 2
    assert {transition.to_state for transition in first.transitions} == {"ASSIGNED"}
    assert len(first.replay_digest) == 64
    assert first.simulated_end_tick == 0
    assert first.wall_clock_elapsed_seconds >= 0
    assert first.wall_clock_elapsed_seconds != first.simulated_end_tick
    assert first.clock_domain == "SIMULATED"


def test_twin_clock_separates_simulated_time_from_wall_clock() -> None:
    clock = TwinClock(ticks_per_hour=60)
    assert clock.simulated_time_seconds == 0
    advanced = clock.advance_to(30)
    assert advanced.simulated_time_seconds == 1800
    with pytest.raises(ValueError, match="backwards"):
        advanced.advance_to(29)
    with pytest.raises(ValueError, match="ticks_per_hour"):
        TwinClock(ticks_per_hour=0)


def test_seed_and_scenario_inputs_are_part_of_replay() -> None:
    assert kernel().run(manifest(7)).replay_digest != kernel().run(manifest(8)).replay_digest

    with pytest.raises(ValueError, match="at least one demand"):
        ScenarioManifest("empty", 1, (), (CourierState("c", GeoPoint(0, 0)),))
    with pytest.raises(ValueError, match="traffic"):
        ScenarioManifest(
            "bad",
            1,
            (DemandEvent("r", GeoPoint(0, 0), 0),),
            (CourierState("c", GeoPoint(0, 0)),),
            traffic_multiplier=0,
        )


def test_manifest_and_kernel_validate_replay_inputs_and_unassigned_state() -> None:
    with pytest.raises(ValueError, match="request_id"):
        DemandEvent(" ", GeoPoint(0, 0), 0)
    with pytest.raises(ValueError, match="tick"):
        DemandEvent("r", GeoPoint(0, 0), -1)
    with pytest.raises(ValueError, match="courier_id"):
        CourierState(" ", GeoPoint(0, 0))
    with pytest.raises(ValueError, match="available_tick"):
        CourierState("c", GeoPoint(0, 0), -1)
    with pytest.raises(ValueError, match="scenario_id"):
        ScenarioManifest(
            " ",
            1,
            (DemandEvent("r", GeoPoint(0, 0), 0),),
            (CourierState("c", GeoPoint(0, 0)),),
        )

    base = (DemandEvent("r", GeoPoint(0, 0), 0),)
    courier = (CourierState("c", GeoPoint(0, 0)),)
    with pytest.raises(ValueError, match="unique"):
        ScenarioManifest("duplicate", 1, base + base, courier)
    with pytest.raises(ValueError, match="courier identifiers"):
        ScenarioManifest("duplicate", 1, base, courier + courier)
    with pytest.raises(ValueError, match="at least one courier"):
        ScenarioManifest("no-courier", 1, base, ())
    with pytest.raises(ValueError, match="delay_ticks"):
        ScenarioManifest("bad-delay", 1, base, courier, delay_ticks=(-1,))
    with pytest.raises(ValueError, match="ticks_per_hour"):
        ScenarioKernel(
            StrategyRegistry((NearestStrategy(),)),
            DeterministicLocalTravelProvider(),
            ticks_per_hour=0,
        )

    one_courier = ScenarioManifest(
        "one-courier",
        1,
        (DemandEvent("r1", GeoPoint(0.1, 0.1), 0), DemandEvent("r2", GeoPoint(0.2, 0.2), 0)),
        courier,
    )
    run = kernel().run(one_courier)
    assert {transition.to_state for transition in run.transitions} == {"ASSIGNED", "UNASSIGNED"}
