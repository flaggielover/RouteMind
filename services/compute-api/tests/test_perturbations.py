from __future__ import annotations

import pytest

from routemind_compute.application.perturbations import (
    PerturbationScenario,
    ScenarioPerturbation,
)
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.domain.dispatch import GeoPoint


def scenario() -> PerturbationScenario:
    return PerturbationScenario(
        "stress-1",
        base_courier_supply=10,
        seed=7,
        perturbations=(
            ScenarioPerturbation(
                "traffic-north",
                "traffic",
                60,
                "north",
                end_at_seconds=180,
                scope="zone",
                traffic_multiplier=1.5,
                delay_seconds=10,
            ),
            ScenarioPerturbation(
                "supply-drop",
                "supply",
                90,
                "city-couriers",
                end_at_seconds=240,
                scope="courier_pool",
                supply_delta=-3,
            ),
            ScenarioPerturbation(
                "merchant-spike",
                "merchant_delay",
                120,
                "merchant-1",
                scope="merchant",
                delay_seconds=45,
            ),
            ScenarioPerturbation(
                "rabbitmq-down",
                "dependency_failure",
                120,
                "rabbitmq",
                end_at_seconds=150,
                scope="dependency",
                failure_mode="unavailable",
            ),
            ScenarioPerturbation(
                "live-provider",
                "dependency_failure",
                120,
                "travel-provider",
                end_at_seconds=150,
                scope="dependency",
                failure_mode="timeout",
                source="live",
            ),
        ),
    )


def test_perturbations_are_seeded_ordered_and_replayable() -> None:
    first = scenario().run()
    second = scenario().run()

    assert first == second
    assert len(first.replay_digest) == 64
    assert [event.perturbation_id for event in first.perturbations] == [
        "traffic-north",
        "supply-drop",
        "live-provider",
        "merchant-spike",
        "rabbitmq-down",
    ]
    assert (
        PerturbationScenario("other", 10, first.perturbations, seed=8).run().replay_digest
        != first.replay_digest
    )


def test_snapshot_exposes_traffic_supply_merchant_and_failure_effects() -> None:
    run = scenario().run()
    before = run.state_at(30)
    assert before.metrics.active_event_count == 0
    assert before.metrics.courier_supply == 10
    assert before.travel_context.traffic_context == "baseline"

    active = run.state_at(130)
    metrics = active.metrics
    assert metrics.active_event_count == 5
    assert metrics.traffic_multiplier == 1.5
    assert metrics.incident_delay_seconds == 10
    assert metrics.courier_supply == 7
    assert metrics.merchant_delay_seconds == 45
    assert metrics.merchant_delay_by_target == (("merchant-1", 45),)
    assert metrics.failed_dependencies == ("rabbitmq", "travel-provider")
    assert metrics.simulated_failure_count == 1
    assert metrics.live_failure_count == 1
    assert active.travel_context.replay_digest

    expired = run.state_at(250)
    assert expired.metrics.active_event_count == 1
    assert expired.metrics.courier_supply == 10
    assert expired.metrics.failed_dependencies == ()
    assert expired.metrics.merchant_delay_seconds == 45


def test_traffic_perturbation_feeds_existing_travel_context() -> None:
    run = scenario().run()
    context = run.state_at(130).travel_context
    provider = DeterministicLocalTravelProvider()
    baseline = provider.estimate(GeoPoint(0, 0), GeoPoint(0.1, 0.1))
    perturbed = provider.estimate(GeoPoint(0, 0), GeoPoint(0.1, 0.1), context)
    assert perturbed.seconds == baseline.seconds + 10
    assert context.updates[0].source == "simulated"


def test_perturbation_inputs_reject_invalid_or_ambiguous_values() -> None:
    with pytest.raises(ValueError, match="id"):
        ScenarioPerturbation(" ", "traffic", 0, "global")
    with pytest.raises(ValueError, match="kind"):
        ScenarioPerturbation("x", "other", 0, "global")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="scope"):
        ScenarioPerturbation("x", "traffic", 0, "global", scope="merchant")
    with pytest.raises(ValueError, match="source"):
        ScenarioPerturbation("x", "traffic", 0, "global", source="fixture")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="effective"):
        ScenarioPerturbation("x", "traffic", -1, "global")
    with pytest.raises(ValueError, match="end"):
        ScenarioPerturbation("x", "traffic", 10, "global", end_at_seconds=10)
    with pytest.raises(ValueError, match="multiplier"):
        ScenarioPerturbation("x", "traffic", 0, "global", traffic_multiplier=0)
    with pytest.raises(ValueError, match="delay"):
        ScenarioPerturbation("x", "traffic", 0, "global", delay_seconds=-1)
    with pytest.raises(ValueError, match="supply"):
        ScenarioPerturbation("x", "supply", 0, "pool", scope="courier_pool", supply_delta=0)
    with pytest.raises(ValueError, match="failure mode"):
        ScenarioPerturbation("x", "dependency_failure", 0, "db", scope="dependency")
    with pytest.raises(ValueError, match="unique"):
        PerturbationScenario(
            "duplicate",
            1,
            (
                ScenarioPerturbation("x", "traffic", 0, "global"),
                ScenarioPerturbation("x", "traffic", 1, "global"),
            ),
        )
    with pytest.raises(ValueError, match="supply"):
        PerturbationScenario("bad", -1)
    with pytest.raises(ValueError, match="time"):
        scenario().run().state_at(-1)
