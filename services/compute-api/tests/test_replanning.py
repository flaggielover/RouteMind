from __future__ import annotations

import pytest

from routemind_compute.application.replanning import (
    DynamicReplanningPolicy,
    ReplanMetrics,
    ReplanningPolicyConfig,
    ReplanningState,
    ReplanRequest,
    ReplanTrigger,
)


def metrics(
    *, assigned: int = 2, unassigned: int = 0, late: int = 0, travel: float = 100
) -> ReplanMetrics:
    return ReplanMetrics(assigned, unassigned, late, travel, active_route_count=assigned)


def request(
    kind: str,
    at: float,
    *,
    trace: str = "trace-1",
    before: ReplanMetrics | None = None,
    after: ReplanMetrics | None = None,
) -> ReplanRequest:
    return ReplanRequest(
        ReplanTrigger(f"event-{at}", kind, at, trace),  # type: ignore[arg-type]
        before or metrics(unassigned=1, late=1, travel=120),
        after or metrics(unassigned=0, late=0, travel=100),
    )


def test_replanning_approves_material_trigger_with_trace_and_java_boundary() -> None:
    evaluation = DynamicReplanningPolicy().evaluate(request("incident", 0))

    assert evaluation.decision.action == "replan"
    assert evaluation.decision.reason == "replan-approved"
    assert evaluation.decision.trigger_kind == "incident"
    assert evaluation.decision.trace_id == "trace-1"
    assert evaluation.decision.before.unassigned_count == 1
    assert evaluation.decision.after.unassigned_count == 0
    assert evaluation.decision.authority == "compute-proposal"
    assert evaluation.decision.requires_java_validation is True
    assert evaluation.next_state.generation == 1
    assert evaluation.next_state.last_replan_seconds == 0


@pytest.mark.parametrize(
    "kind", ["arrival", "lateness", "incident", "courier_loss", "material_change"]
)
def test_all_replan_trigger_kinds_are_supported(kind: str) -> None:
    assert DynamicReplanningPolicy().evaluate(request(kind, 10)).decision.action == "replan"


def test_replanning_debounce_and_cooldown_prevent_thrashing() -> None:
    policy = DynamicReplanningPolicy(
        ReplanningPolicyConfig(debounce_seconds=30, cooldown_seconds=120)
    )
    first = policy.evaluate(request("arrival", 10))
    debounced = policy.evaluate(request("arrival", 20), first.next_state)
    cooled = policy.evaluate(request("arrival", 50), debounced.next_state)
    approved_again = policy.evaluate(request("arrival", 131), cooled.next_state)

    assert first.decision.action == "replan"
    assert debounced.decision.reason == "debounced"
    assert cooled.decision.reason == "cooldown-active"
    assert approved_again.decision.action == "replan"
    assert approved_again.next_state.generation == 2


def test_replanning_holds_without_material_improvement_and_preserves_metrics() -> None:
    before = metrics(unassigned=0, late=0, travel=100)
    after = metrics(unassigned=0, late=0, travel=100)
    evaluation = DynamicReplanningPolicy().evaluate(
        request("material_change", 1, before=before, after=after)
    )

    assert evaluation.decision.action == "hold"
    assert evaluation.decision.reason == "no-material-improvement"
    assert evaluation.decision.before == before
    assert evaluation.decision.after == after
    assert evaluation.next_state.generation == 0


def test_replanning_rejects_time_regression_and_invalid_contract_values() -> None:
    policy = DynamicReplanningPolicy()
    first = policy.evaluate(request("arrival", 10))
    with pytest.raises(ValueError, match="backwards"):
        policy.evaluate(request("arrival", 9), first.next_state)

    with pytest.raises(ValueError, match="event id"):
        ReplanTrigger(" ", "arrival", 0, "trace")
    with pytest.raises(ValueError, match="kind"):
        ReplanTrigger("event", "unknown", 0, "trace")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="observed"):
        ReplanTrigger("event", "arrival", -1, "trace")
    with pytest.raises(ValueError, match="trace"):
        ReplanTrigger("event", "arrival", 0, " ")
    with pytest.raises(ValueError, match="courier"):
        ReplanTrigger("event", "courier_loss", 0, "trace", courier_id=" ")
    with pytest.raises(ValueError, match="debounce"):
        ReplanningPolicyConfig(debounce_seconds=-1)
    with pytest.raises(ValueError, match="cooldown"):
        ReplanningPolicyConfig(cooldown_seconds=-1)
    with pytest.raises(ValueError, match="counts"):
        ReplanMetrics(-1, 0, 0, 0, 0)
    with pytest.raises(ValueError, match="travel"):
        ReplanMetrics(0, 0, 0, -1, 0)
    with pytest.raises(ValueError, match="generation"):
        ReplanningState(generation=-1)
