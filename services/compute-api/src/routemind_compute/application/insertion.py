"""Explicit, bounded insertion for an immutable active route snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.vrptw import (
    VrpInsertionDecision,
    VrpProblem,
    VrpRoute,
    VrpStop,
    VrptwRoutePlanner,
)


@dataclass(frozen=True, slots=True)
class DynamicInsertionRequest:
    scenario_id: str
    seed: int
    previous_plan_reference: str
    selected_strategy: str
    problem: VrpProblem
    active_route: VrpRoute
    new_stop: VrpStop

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("insertion scenario_id must not be blank")
        if isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError("insertion seed must be non-negative")
        if not self.previous_plan_reference.strip():
            raise ValueError("previous_plan_reference must be supplied")
        if not self.selected_strategy.strip():
            raise ValueError("selected_strategy must be supplied")


@dataclass(frozen=True, slots=True)
class DynamicInsertionResult:
    request: DynamicInsertionRequest
    decision: VrpInsertionDecision
    input_digest: str
    output_digest: str
    replay_digest: str
    resulting_plan_reference: str | None


def _route_payload(route: VrpRoute | None) -> dict[str, object] | None:
    if route is None:
        return None
    return {
        "vehicle_id": route.vehicle_id,
        "stop_ids": route.stop_ids,
        "arrival_seconds": route.arrival_seconds,
        "service_start_seconds": route.service_start_seconds,
        "departure_seconds": route.departure_seconds,
        "load_units": route.load_units,
        "travel_seconds": route.travel_seconds,
        "completion_seconds": route.completion_seconds,
    }


def insert_order(
    request: DynamicInsertionRequest,
    planner: VrptwRoutePlanner | None = None,
) -> DynamicInsertionResult:
    """Insert without mutating the supplied route or manufacturing history."""

    active = planner or VrptwRoutePlanner()
    input_payload = {
        "scenario_id": request.scenario_id,
        "seed": request.seed,
        "previous_plan_reference": request.previous_plan_reference,
        "selected_strategy": request.selected_strategy,
        "problem_id": request.problem.problem_id,
        "active_route": _route_payload(request.active_route),
        "new_stop": {
            "stop_id": request.new_stop.stop_id,
            "latitude": request.new_stop.location.latitude,
            "longitude": request.new_stop.location.longitude,
            "demand_units": request.new_stop.demand_units,
            "service_seconds": request.new_stop.service_seconds,
        },
    }
    input_digest = canonical_digest(input_payload)
    decision = active.insert(request.problem, request.active_route, request.new_stop)
    output_payload = {
        "accepted": decision.accepted,
        "route": _route_payload(decision.route),
        "insertion_position": decision.insertion_position,
        "incremental_travel_seconds": decision.incremental_travel_seconds,
        "reason": decision.reason,
    }
    output_digest = canonical_digest(output_payload)
    replay_digest = canonical_digest({"input_digest": input_digest, "output_digest": output_digest})
    resulting = f"plan:{output_digest[:16]}" if decision.accepted else None
    return DynamicInsertionResult(
        request,
        decision,
        input_digest,
        output_digest,
        replay_digest,
        resulting,
    )


__all__ = [
    "DynamicInsertionRequest",
    "DynamicInsertionResult",
    "insert_order",
]
