from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import Literal

Metadata = tuple[tuple[str, str], ...]

ReplanTriggerKind = Literal[
    "arrival",
    "lateness",
    "incident",
    "courier_loss",
    "material_change",
    "traffic_degradation",
    "provider_fallback",
    "merchant_delay",
    "route_feasibility_change",
]
ReplanAction = Literal["replan", "hold"]


@dataclass(frozen=True, slots=True)
class ReplanMetrics:
    assigned_count: int
    unassigned_count: int
    late_count: int
    total_travel_seconds: float
    active_route_count: int

    def __post_init__(self) -> None:
        counts = (
            self.assigned_count,
            self.unassigned_count,
            self.late_count,
            self.active_route_count,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts
        ):
            raise ValueError("replan metrics counts must be non-negative integers")
        if not isfinite(self.total_travel_seconds) or self.total_travel_seconds < 0:
            raise ValueError("replan travel seconds must be finite and non-negative")

    @property
    def objective_key(self) -> tuple[int, int, float, int]:
        return (
            self.unassigned_count,
            self.late_count,
            self.total_travel_seconds,
            -self.assigned_count,
        )


@dataclass(frozen=True, slots=True)
class ReplanTrigger:
    event_id: str
    kind: ReplanTriggerKind
    observed_at_seconds: float
    trace_id: str
    detail: str = ""
    courier_id: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("replan event id must not be blank")
        if self.kind not in {
            "arrival",
            "lateness",
            "incident",
            "courier_loss",
            "material_change",
            "traffic_degradation",
            "provider_fallback",
            "merchant_delay",
            "route_feasibility_change",
        }:
            raise ValueError("replan trigger kind is not supported")
        if not isfinite(self.observed_at_seconds) or self.observed_at_seconds < 0:
            raise ValueError("replan observed time must be finite and non-negative")
        if not self.trace_id.strip():
            raise ValueError("replan trace id must not be blank")
        if self.courier_id is not None and not self.courier_id.strip():
            raise ValueError("replan courier id must not be blank")


@dataclass(frozen=True, slots=True)
class ReplanRequest:
    trigger: ReplanTrigger
    before: ReplanMetrics
    after: ReplanMetrics
    previous_plan_reference: str = ""
    selected_strategy: str = ""
    triggering_state: Metadata = ()
    resulting_plan_reference: str | None = None


@dataclass(frozen=True, slots=True)
class ReplanningPolicyConfig:
    debounce_seconds: float = 30.0
    cooldown_seconds: float = 120.0

    def __post_init__(self) -> None:
        if not isfinite(self.debounce_seconds) or self.debounce_seconds < 0:
            raise ValueError("replan debounce seconds must be finite and non-negative")
        if not isfinite(self.cooldown_seconds) or self.cooldown_seconds < 0:
            raise ValueError("replan cooldown seconds must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class ReplanningState:
    last_observed_seconds: float | None = None
    last_replan_seconds: float | None = None
    generation: int = 0

    def __post_init__(self) -> None:
        for value in (self.last_observed_seconds, self.last_replan_seconds):
            if value is not None and (not isfinite(value) or value < 0):
                raise ValueError("replan state time must be finite and non-negative")
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise ValueError("replan generation must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ReplanDecision:
    action: ReplanAction
    reason: str
    trigger_kind: ReplanTriggerKind
    trace_id: str
    before: ReplanMetrics
    after: ReplanMetrics
    generation: int
    authority: str = "compute-proposal"
    requires_java_validation: bool = True
    previous_plan_reference: str | None = None
    selected_strategy: str | None = None
    triggering_state: Metadata = ()
    resulting_plan_reference: str | None = None
    replay_digest: str | None = None


@dataclass(frozen=True, slots=True)
class ReplanEvaluation:
    decision: ReplanDecision
    next_state: ReplanningState


class DynamicReplanningPolicy:
    """Deterministic trigger gate; it proposes work but never applies assignments."""

    name = "dynamic-replanning"
    version = "1.0.0"

    def __init__(self, configuration: ReplanningPolicyConfig | None = None) -> None:
        self.configuration = configuration or ReplanningPolicyConfig()

    def evaluate(
        self,
        request: ReplanRequest,
        state: ReplanningState | None = None,
    ) -> ReplanEvaluation:
        current = state or ReplanningState()
        if request.previous_plan_reference and not request.previous_plan_reference.strip():
            raise ValueError("previous_plan_reference must not be blank when supplied")
        if request.selected_strategy and not request.selected_strategy.strip():
            raise ValueError("selected_strategy must not be blank when supplied")
        if len({key for key, _ in request.triggering_state}) != len(request.triggering_state):
            raise ValueError("triggering_state keys must be unique")
        if any(not key.strip() or not value.strip() for key, value in request.triggering_state):
            raise ValueError("triggering_state keys and values must not be blank")
        now = request.trigger.observed_at_seconds
        if current.last_observed_seconds is not None and now < current.last_observed_seconds:
            raise ValueError("replan events cannot move backwards")
        next_state = replace(current, last_observed_seconds=now)
        reason: str | None = None
        if (
            current.last_observed_seconds is not None
            and now - current.last_observed_seconds < self.configuration.debounce_seconds
        ):
            reason = "debounced"
        elif (
            current.last_replan_seconds is not None
            and now - current.last_replan_seconds < self.configuration.cooldown_seconds
        ):
            reason = "cooldown-active"
        elif request.after.objective_key >= request.before.objective_key:
            reason = "no-material-improvement"

        if reason is not None:
            decision = ReplanDecision(
                "hold",
                reason,
                request.trigger.kind,
                request.trigger.trace_id,
                request.before,
                request.after,
                current.generation,
                previous_plan_reference=request.previous_plan_reference or None,
                selected_strategy=request.selected_strategy or None,
                triggering_state=tuple(sorted(request.triggering_state)),
                resulting_plan_reference=request.resulting_plan_reference,
            )
            return ReplanEvaluation(_with_replay_digest(request, decision), next_state)

        next_state = replace(
            next_state,
            last_replan_seconds=now,
            generation=current.generation + 1,
        )
        decision = ReplanDecision(
            "replan",
            "replan-approved",
            request.trigger.kind,
            request.trigger.trace_id,
            request.before,
            request.after,
            next_state.generation,
            previous_plan_reference=request.previous_plan_reference or None,
            selected_strategy=request.selected_strategy or None,
            triggering_state=tuple(sorted(request.triggering_state)),
            resulting_plan_reference=request.resulting_plan_reference,
        )
        return ReplanEvaluation(_with_replay_digest(request, decision), next_state)


def _with_replay_digest(request: ReplanRequest, decision: ReplanDecision) -> ReplanDecision:
    from routemind_compute.application.execution import canonical_digest

    payload = {
        "trigger": {
            "event_id": request.trigger.event_id,
            "kind": request.trigger.kind,
            "observed_at_seconds": request.trigger.observed_at_seconds,
            "trace_id": request.trigger.trace_id,
            "detail": request.trigger.detail,
            "courier_id": request.trigger.courier_id,
        },
        "before": {
            "assigned_count": request.before.assigned_count,
            "unassigned_count": request.before.unassigned_count,
            "late_count": request.before.late_count,
            "total_travel_seconds": request.before.total_travel_seconds,
            "active_route_count": request.before.active_route_count,
        },
        "after": {
            "assigned_count": request.after.assigned_count,
            "unassigned_count": request.after.unassigned_count,
            "late_count": request.after.late_count,
            "total_travel_seconds": request.after.total_travel_seconds,
            "active_route_count": request.after.active_route_count,
        },
        "previous_plan_reference": request.previous_plan_reference,
        "selected_strategy": request.selected_strategy,
        "triggering_state": tuple(sorted(request.triggering_state)),
        "resulting_plan_reference": request.resulting_plan_reference,
        "decision": {
            "action": decision.action,
            "reason": decision.reason,
            "generation": decision.generation,
        },
    }
    return replace(decision, replay_digest=canonical_digest(payload))
