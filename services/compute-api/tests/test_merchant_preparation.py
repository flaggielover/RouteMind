from __future__ import annotations

import pytest

from routemind_compute.application.merchant_preparation import (
    MerchantPreparationModel,
    MerchantPreparationProfile,
    PreparationOrder,
)
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint


def profile(
    variability_seconds: float = 30.0,
    capacity: int = 1,
) -> MerchantPreparationProfile:
    return MerchantPreparationProfile(
        "merchant-1",
        base_prep_seconds=60,
        variability_seconds=variability_seconds,
        capacity=capacity,
        order_profile_multipliers=(("standard", 1.0), ("large", 1.5)),
        late_risk_horizon_seconds=60,
    )


def orders() -> tuple[PreparationOrder, ...]:
    return (
        PreparationOrder("order-2", "merchant-1", 10, "large"),
        PreparationOrder("order-1", "merchant-1", 0),
    )


def test_preparation_schedule_is_seeded_and_replayable() -> None:
    first = MerchantPreparationModel((profile(),), seed=7).run(orders())
    second = MerchantPreparationModel((profile(),), seed=7).run(orders())

    assert first == second
    assert first.orders == (orders()[1], orders()[0])
    assert len(first.replay_digest) == 64
    assert (
        MerchantPreparationModel((profile(),), seed=8).run(orders()).replay_digest
        != first.replay_digest
    )
    assert first.state_at("order-1", 0).expected_prep_seconds == 60
    assert first.state_at("order-2", 0).order_profile == "large"


def test_queue_ready_times_and_late_risk_evolve_with_simulated_time() -> None:
    run = MerchantPreparationModel((profile(variability_seconds=60),), seed=2).run(
        (PreparationOrder("order-1", "merchant-1", 0), PreparationOrder("order-2", "merchant-1", 0))
    )
    initial = run.state_at("order-1", 0)
    queued = run.state_at("order-2", 0)
    assert initial.status == "preparing"
    assert initial.queue_load == 2
    assert queued.status == "queued"
    assert initial.actual_ready_at_seconds > initial.expected_ready_at_seconds

    mid_time = (initial.expected_ready_at_seconds + initial.actual_ready_at_seconds) / 2
    during = run.state_at("order-1", mid_time)
    assert during.status == "preparing"
    assert 0 < during.late_risk < 1

    finished = run.state_at(
        "order-1", max(initial.actual_ready_at_seconds, queued.actual_ready_at_seconds) + 1
    )
    assert finished.status == "ready"
    assert finished.queue_load == 0
    assert 0 < finished.late_risk < 1
    assert run.states_at(finished.observed_at_seconds)[0].order_id == "order-1"


def test_dispatch_consumes_actual_preparation_readiness() -> None:
    state = (
        MerchantPreparationModel((profile(variability_seconds=0),), seed=1)
        .run((PreparationOrder("order-1", "merchant-1", 0),))
        .state_at("order-1", 0)
    )
    candidate = CourierCandidate(
        "courier-1",
        GeoPoint(0, 0),
        available_until_seconds=state.dispatch_ready_at_seconds - 1,
    )
    problem = DispatchProblem("order-1", GeoPoint(0, 0), (candidate,))
    assert state.apply_to(problem).eligible_candidates() == ()
    with pytest.raises(ValueError, match="does not match"):
        state.apply_to(DispatchProblem("other-order", GeoPoint(0, 0), (candidate,)))


def test_preparation_inputs_validate_explicitly() -> None:
    with pytest.raises(ValueError, match="merchant id"):
        MerchantPreparationProfile(" ", 1)
    with pytest.raises(ValueError, match="base preparation"):
        MerchantPreparationProfile("m", -1)
    with pytest.raises(ValueError, match="variability"):
        MerchantPreparationProfile("m", 1, float("nan"))
    with pytest.raises(ValueError, match="capacity"):
        MerchantPreparationProfile("m", 1, capacity=0)
    with pytest.raises(ValueError, match="horizon"):
        MerchantPreparationProfile("m", 1, late_risk_horizon_seconds=0)
    with pytest.raises(ValueError, match="profile identifiers"):
        MerchantPreparationProfile("m", 1, order_profile_multipliers=(("x", 1), ("x", 2)))
    with pytest.raises(ValueError, match="profile identifier"):
        MerchantPreparationProfile("m", 1, order_profile_multipliers=((" ", 1),))
    with pytest.raises(ValueError, match="multiplier"):
        MerchantPreparationProfile("m", 1, order_profile_multipliers=(("x", 0),))
    with pytest.raises(ValueError, match="order id"):
        PreparationOrder(" ", "m", 0)
    with pytest.raises(ValueError, match="merchant id"):
        PreparationOrder("o", " ", 0)
    with pytest.raises(ValueError, match="enqueued"):
        PreparationOrder("o", "m", -1)
    with pytest.raises(ValueError, match="order profile"):
        PreparationOrder("o", "m", 0, " ")
    with pytest.raises(ValueError, match="at least one"):
        MerchantPreparationModel((), seed=1)
    with pytest.raises(ValueError, match="identifiers"):
        MerchantPreparationModel((profile(), profile()), seed=1)

    model = MerchantPreparationModel((profile(),), seed=1)
    with pytest.raises(ValueError, match="identifiers"):
        model.run((PreparationOrder("o", "merchant-1", 0), PreparationOrder("o", "merchant-1", 1)))
    with pytest.raises(ValueError, match="unknown merchant"):
        model.run((PreparationOrder("o", "missing", 0),))
    with pytest.raises(ValueError, match="unknown order profile"):
        model.run((PreparationOrder("o", "merchant-1", 0, "unknown"),))

    with pytest.raises(ValueError, match="observed time"):
        model.run((PreparationOrder("o", "merchant-1", 0),)).state_at("o", -1)
    with pytest.raises(KeyError, match="unknown preparation order"):
        model.run((PreparationOrder("o", "merchant-1", 0),)).state_at("missing", 0)
    with pytest.raises(ValueError, match="observed time"):
        model.run((PreparationOrder("o", "merchant-1", 0),)).states_at(-1)
