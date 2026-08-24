from __future__ import annotations

from dataclasses import replace
from math import inf, nan
from typing import Literal, cast

import pytest

from routemind_compute.application.rads_h import (
    RadsHConfig,
    RadsHDecision,
    RadsHState,
    evaluate_rads_h,
)


def state(**overrides: object) -> RadsHState:
    values: dict[str, object] = {
        "active_strategy": "rads",
        "regime_id": "zone-a",
        "pressure_ticks": 0,
        "dwell_ticks": 3,
        "switch_count": 0,
    }
    values.update(overrides)
    return RadsHState(**values)  # type: ignore[arg-type]


def test_hysteresis_requires_threshold_persistence_and_applies_switch_cost() -> None:
    config = RadsHConfig()
    first = evaluate_rads_h(
        config,
        state(),
        candidate_strategy="weighted-greedy",
        candidate_score=90.0,
        current_score=100.0,
        regime_id="zone-a",
    )
    assert first.action == "hold"
    assert first.reason == "persistence-required"
    assert first.next_state.pressure_ticks == 1
    second = evaluate_rads_h(
        config,
        first.next_state,
        candidate_strategy="weighted-greedy",
        candidate_score=90.0,
        current_score=100.0,
        regime_id="zone-a",
    )
    assert second.action == "switch"
    assert second.reason == "persistence-satisfied"
    assert second.applied_switching_cost == 0.01
    assert second.next_state.active_strategy == "weighted-greedy"
    assert second.next_state.switch_count == 1
    assert second.next_state.pressure_ticks == 0
    assert second.next_state.dwell_ticks == 0


def test_hysteresis_holds_for_regime_active_dwell_and_bands() -> None:
    config = RadsHConfig()
    reset = evaluate_rads_h(
        config,
        state(regime_id="zone-a"),
        candidate_strategy="weighted-greedy",
        candidate_score=90.0,
        current_score=100.0,
        regime_id="zone-b",
    )
    assert reset.reason == "regime-reset"
    assert reset.next_state.pressure_ticks == 0
    active = evaluate_rads_h(
        config,
        state(),
        candidate_strategy="rads",
        candidate_score=90.0,
        current_score=100.0,
        regime_id="zone-a",
    )
    assert active.reason == "active-strategy"
    assert active.next_state.dwell_ticks == 4
    dwell = evaluate_rads_h(
        config,
        state(dwell_ticks=1),
        candidate_strategy="weighted-greedy",
        candidate_score=90.0,
        current_score=100.0,
        regime_id="zone-a",
    )
    assert dwell.reason == "minimum-dwell"
    exit_band = evaluate_rads_h(
        config,
        state(),
        candidate_strategy="weighted-greedy",
        candidate_score=103.0,
        current_score=100.0,
        regime_id="zone-a",
    )
    assert exit_band.reason == "outside-exit-band"
    below = evaluate_rads_h(
        config,
        state(),
        candidate_strategy="weighted-greedy",
        candidate_score=98.0,
        current_score=100.0,
        regime_id="zone-a",
    )
    assert below.reason == "below-enter-threshold"


def test_hysteresis_validates_inputs_and_decision_shape() -> None:
    with pytest.raises(ValueError, match="enter_threshold"):
        RadsHConfig(enter_threshold=0.0)
    with pytest.raises(ValueError, match="exit_threshold"):
        RadsHConfig(enter_threshold=0.05, exit_threshold=0.05)
    with pytest.raises(ValueError, match="persistence_ticks"):
        RadsHConfig(persistence_ticks=0)
    with pytest.raises(ValueError, match="minimum_dwell_ticks"):
        RadsHConfig(minimum_dwell_ticks=-1)
    with pytest.raises(ValueError, match="switching_cost"):
        RadsHConfig(switching_cost=inf)
    with pytest.raises(ValueError, match="exit_threshold"):
        RadsHConfig(exit_threshold=-1.0)
    with pytest.raises(ValueError, match="exceeds"):
        RadsHState("rads", "x" * 257)
    with pytest.raises(ValueError, match="active_strategy"):
        RadsHState(" ", "zone-a")
    with pytest.raises(ValueError, match="pressure_ticks"):
        RadsHState("rads", "zone-a", pressure_ticks=-1)

    config = RadsHConfig()
    current = state()
    with pytest.raises(ValueError, match="candidate_strategy"):
        evaluate_rads_h(
            config,
            current,
            candidate_strategy="",
            candidate_score=1.0,
            current_score=1.0,
            regime_id="zone-a",
        )
    with pytest.raises(ValueError, match="finite"):
        evaluate_rads_h(
            config,
            current,
            candidate_strategy="other",
            candidate_score=nan,
            current_score=1.0,
            regime_id="zone-a",
        )
    decision = evaluate_rads_h(
        config,
        current,
        candidate_strategy="rads",
        candidate_score=1.0,
        current_score=1.0,
        regime_id="zone-a",
    )
    with pytest.raises(ValueError, match="action"):
        RadsHDecision(
            cast(Literal["switch", "hold"], "other"),
            decision.reason,
            decision.previous_strategy,
            decision.selected_strategy,
            decision.regime_id,
            decision.relative_advantage,
            decision.applied_switching_cost,
            decision.next_state,
        )
    with pytest.raises(ValueError, match="relative_advantage"):
        replace(decision, relative_advantage=inf)
    with pytest.raises(ValueError, match="applied_switching_cost"):
        replace(decision, applied_switching_cost=-1.0)
