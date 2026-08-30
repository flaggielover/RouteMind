"""Bounded deterministic local-search assignment for engineering comparison."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from routemind_compute.application.flow import (
    BatchAssignment,
    BatchDispatchDecision,
    BatchDispatchProblem,
    BatchDispatchRequest,
)
from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import CourierCandidate, DispatchDecision, DispatchProblem


@dataclass(frozen=True, slots=True)
class LocalSearchConfig:
    """Hard bounds for the deterministic improvement loop."""

    max_iterations: int = 32

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_iterations, bool)
            or not isinstance(self.max_iterations, int)
            or not 1 <= self.max_iterations <= 256
        ):
            raise ValueError("local-search max_iterations must be an integer between 1 and 256")


def _distance(request: BatchDispatchRequest, candidate: CourierCandidate) -> float:
    pickup = request.pickup
    return great_circle_distance_kilometres(
        pickup.latitude,
        pickup.longitude,
        candidate.location.latitude,
        candidate.location.longitude,
    )


class LocalSearchStrategy:
    """Improve a deterministic greedy assignment with bounded pair swaps.

    The solver is intentionally local: it does not claim global optimality and
    reports the same standard single-request decision contract as other
    registered strategies.
    """

    name = "local-search"
    version = "1.0.0"
    capabilities = ("dispatch", "batch-assignment", "local-search")
    maturity = "ENGINEERING"

    def __init__(self, configuration: LocalSearchConfig | None = None) -> None:
        self.configuration = configuration or LocalSearchConfig()

    def assign_batch(self, problem: BatchDispatchProblem) -> BatchDispatchDecision:
        started = perf_counter()
        candidates = tuple(sorted(problem.candidates, key=lambda item: item.courier_id))
        requests = tuple(sorted(problem.requests, key=lambda item: item.request_id))
        remaining = {
            candidate.courier_id: max(
                0, int(candidate.capacity_units - candidate.current_load_units)
            )
            for candidate in candidates
        }
        assignments: dict[str, str] = {}
        costs: dict[tuple[str, str], float] = {}
        reasons: dict[str, str] = {}
        for request in requests:
            options: list[tuple[float, str]] = []
            for candidate in candidates:
                single = DispatchProblem(request.request_id, request.pickup, (candidate,))
                rejection = single.candidate_rejection_reasons(candidate)
                if rejection:
                    reasons.setdefault(request.request_id, f"{candidate.courier_id}:{rejection[0]}")
                    continue
                cost = _distance(request, candidate)
                costs[(request.request_id, candidate.courier_id)] = cost
                if remaining[candidate.courier_id] > 0:
                    options.append((cost, candidate.courier_id))
            if options:
                _, courier_id = min(options, key=lambda item: (item[0], item[1]))
                assignments[request.request_id] = courier_id
                remaining[courier_id] -= 1

        # A bounded first-improvement pass can exchange two already assigned
        # requests without changing capacity or hiding infeasibility.
        for _ in range(self.configuration.max_iterations):
            improved = False
            request_ids = tuple(sorted(assignments))
            for index, left_id in enumerate(request_ids):
                for right_id in request_ids[index + 1 :]:
                    left_courier = assignments[left_id]
                    right_courier = assignments[right_id]
                    current = costs[(left_id, left_courier)] + costs[(right_id, right_courier)]
                    swapped = costs.get((left_id, right_courier))
                    swapped_right = costs.get((right_id, left_courier))
                    if swapped is None or swapped_right is None:
                        continue
                    if swapped + swapped_right + 1e-12 < current:
                        assignments[left_id] = right_courier
                        assignments[right_id] = left_courier
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break

        assigned_rows = tuple(
            BatchAssignment(
                request_id, assignments[request_id], costs[(request_id, assignments[request_id])]
            )
            for request_id in sorted(assignments)
        )
        unassigned = tuple(
            (request.request_id, reasons.get(request.request_id, "no courier capacity"))
            for request in requests
            if request.request_id not in assignments
        )
        total = sum(item.cost for item in assigned_rows)
        return BatchDispatchDecision(
            problem.batch_id,
            self.name,
            self.version,
            assigned_rows,
            unassigned,
            total,
            (perf_counter() - started) * 1000,
        )

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        result = self.assign_batch(
            BatchDispatchProblem(
                problem.request_id,
                (
                    # The batch adapter deliberately preserves the existing
                    # single-request contract used by the compute verifier.
                    BatchDispatchRequest(problem.request_id, problem.pickup, problem.demand_units),
                ),
                problem.candidates,
            )
        )
        if not result.assignments:
            return DispatchDecision(
                problem.request_id,
                self.name,
                None,
                None,
                ("no eligible courier", *problem.infeasibility_reasons()),
                self.version,
            )
        assignment = result.assignments[0]
        return DispatchDecision(
            problem.request_id,
            self.name,
            assignment.courier_id,
            assignment.cost,
            ("bounded local-search assignment",),
            self.version,
            metadata=(
                ("iteration_limit", str(self.configuration.max_iterations)),
                ("objective_scope", "pickup_distance_only"),
                ("optimality_claim", "none"),
            ),
        )


__all__ = ["LocalSearchConfig", "LocalSearchStrategy"]
