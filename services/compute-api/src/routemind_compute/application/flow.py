from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import perf_counter

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchDecision,
    DispatchProblem,
    GeoPoint,
)


@dataclass(frozen=True, slots=True)
class BatchDispatchRequest:
    request_id: str
    pickup: GeoPoint
    demand_units: float = 1.0
    partition: str = ""

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("batch request_id must not be blank")
        if not isfinite(self.demand_units) or self.demand_units <= 0:
            raise ValueError("batch demand_units must be finite and positive")
        if self.partition and not self.partition.strip():
            raise ValueError("batch partition must not be blank")


@dataclass(frozen=True, slots=True)
class BatchDispatchProblem:
    batch_id: str
    requests: tuple[BatchDispatchRequest, ...]
    candidates: tuple[CourierCandidate, ...]

    def __post_init__(self) -> None:
        if not self.batch_id.strip():
            raise ValueError("batch_id must not be blank")
        request_ids = [request.request_id for request in self.requests]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("batch request identifiers must be unique")


@dataclass(frozen=True, slots=True)
class BatchAssignment:
    request_id: str
    courier_id: str
    cost: float


@dataclass(frozen=True, slots=True)
class BatchDispatchDecision:
    batch_id: str
    strategy: str
    strategy_version: str
    assignments: tuple[BatchAssignment, ...]
    unassigned: tuple[tuple[str, str], ...]
    total_cost: float
    latency_millis: float


@dataclass(slots=True)
class _Edge:
    target: int
    reverse: int
    capacity: int
    cost: float


def _minimum_cost_flow(
    costs: tuple[tuple[float | None, ...], ...], capacities: tuple[int, ...]
) -> tuple[tuple[tuple[int, int, float], ...], tuple[int, ...], float]:
    """Solve bounded bipartite assignment with residual shortest paths."""
    request_count = len(costs)
    courier_count = len(capacities)
    if any(len(row) != courier_count for row in costs):
        raise ValueError("flow cost matrix must be rectangular")
    if any(capacity < 0 for capacity in capacities):
        raise ValueError("flow capacities must be non-negative")

    source = request_count + courier_count
    sink = source + 1
    graph: list[list[_Edge]] = [[] for _ in range(sink + 1)]
    request_edges: list[list[tuple[int, int, float]]] = [[] for _ in range(request_count)]

    def add_edge(origin: int, target: int, capacity: int, cost: float) -> int:
        forward = len(graph[origin])
        graph[origin].append(_Edge(target, len(graph[target]), capacity, cost))
        graph[target].append(_Edge(origin, forward, 0, -cost))
        return forward

    for request_index in range(request_count):
        add_edge(source, request_index, 1, 0.0)
        for courier_index, cost in enumerate(costs[request_index]):
            if cost is not None:
                edge_index = add_edge(request_index, request_count + courier_index, 1, cost)
                request_edges[request_index].append((edge_index, courier_index, cost))
    for courier_index, capacity in enumerate(capacities):
        add_edge(request_count + courier_index, sink, capacity, 0.0)

    assigned: list[tuple[int, int, float]] = []
    total_cost = 0.0
    while True:
        distances = [float("inf")] * len(graph)
        previous: list[tuple[int, int] | None] = [None] * len(graph)
        distances[source] = 0.0
        for _ in range(len(graph) - 1):
            changed = False
            for origin, edges in enumerate(graph):
                if distances[origin] == float("inf"):
                    continue
                for edge_index, edge in enumerate(edges):
                    if edge.capacity <= 0:
                        continue
                    candidate = distances[origin] + edge.cost
                    if candidate < distances[edge.target]:
                        distances[edge.target] = candidate
                        previous[edge.target] = (origin, edge_index)
                        changed = True
            if not changed:
                break
        if previous[sink] is None:
            break
        node = sink
        while node != source:
            origin, edge_index = previous[node]  # type: ignore[misc]
            edge = graph[origin][edge_index]
            edge.capacity -= 1
            graph[node][edge.reverse].capacity += 1
            node = origin
        total_cost += distances[sink]

    for request_index, request_edge_refs in enumerate(request_edges):
        for edge_index, courier_index, cost in request_edge_refs:
            if graph[request_index][edge_index].capacity == 0:
                assigned.append((request_index, courier_index, cost))
    assigned.sort()
    assigned_requests = {request_index for request_index, _, _ in assigned}
    return (
        tuple(assigned),
        tuple(
            request_index
            for request_index in range(request_count)
            if request_index not in assigned_requests
        ),
        total_cost,
    )


class MinimumCostFlowStrategy:
    name = "minimum-cost-flow"
    version = "1.0.0"

    def assign_batch(self, problem: BatchDispatchProblem) -> BatchDispatchDecision:
        started = perf_counter()
        costs: list[tuple[float | None, ...]] = []
        reasons: dict[str, str] = {}
        for request in problem.requests:
            row: list[float | None] = []
            for candidate in problem.candidates:
                single = DispatchProblem(
                    request.request_id,
                    request.pickup,
                    (candidate,),
                    demand_units=request.demand_units,
                )
                rejection = single.candidate_rejection_reasons(candidate)
                if rejection:
                    row.append(None)
                    reasons.setdefault(request.request_id, f"{candidate.courier_id}:{rejection[0]}")
                else:
                    row.append(
                        great_circle_distance_kilometres(
                            request.pickup.latitude,
                            request.pickup.longitude,
                            candidate.location.latitude,
                            candidate.location.longitude,
                        )
                    )
            costs.append(tuple(row))
        capacities = tuple(
            max(0, int(candidate.capacity_units - candidate.current_load_units))
            for candidate in problem.candidates
        )
        assigned, unassigned_indices, total_cost = _minimum_cost_flow(tuple(costs), capacities)
        assignments = tuple(
            BatchAssignment(
                problem.requests[request_index].request_id,
                problem.candidates[courier_index].courier_id,
                cost,
            )
            for request_index, courier_index, cost in assigned
        )
        unassigned = tuple(
            (
                problem.requests[request_index].request_id,
                reasons.get(problem.requests[request_index].request_id, "no courier capacity"),
            )
            for request_index in unassigned_indices
        )
        return BatchDispatchDecision(
            problem.batch_id,
            self.name,
            self.version,
            assignments,
            unassigned,
            total_cost,
            (perf_counter() - started) * 1000,
        )

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        result = self.assign_batch(
            BatchDispatchProblem(
                problem.request_id,
                (BatchDispatchRequest(problem.request_id, problem.pickup, problem.demand_units),),
                problem.candidates,
            )
        )
        if not result.assignments:
            rationale = ("no eligible courier", *problem.infeasibility_reasons())
            courier_id = None
            score = None
        else:
            assignment = result.assignments[0]
            rationale = ("minimum-cost flow assignment",)
            courier_id = assignment.courier_id
            score = assignment.cost
        return DispatchDecision(
            problem.request_id,
            self.name,
            courier_id,
            score,
            rationale,
            self.version,
            metadata=(
                ("assignment_mode", "successive-shortest-augmenting-path"),
                ("batch_assigned_count", str(len(result.assignments))),
                ("batch_unassigned_count", str(len(result.unassigned))),
            ),
        )


class PartitionedAssignmentStrategy(MinimumCostFlowStrategy):
    name = "partitioned-assignment"
    version = "1.0.0"

    def assign_batch(self, problem: BatchDispatchProblem) -> BatchDispatchDecision:
        started = perf_counter()
        assignments: list[BatchAssignment] = []
        unassigned: list[tuple[str, str]] = []
        total_cost = 0.0
        for partition in sorted({request.partition for request in problem.requests}):
            requests = tuple(
                request for request in problem.requests if request.partition == partition
            )
            candidates = tuple(
                candidate
                for candidate in problem.candidates
                if not partition or candidate.zone == partition
            )
            result = super().assign_batch(
                BatchDispatchProblem(problem.batch_id, requests, candidates)
            )
            assignments.extend(result.assignments)
            unassigned.extend(result.unassigned)
            total_cost += result.total_cost
        assignments.sort(key=lambda item: item.request_id)
        unassigned.sort()
        return BatchDispatchDecision(
            problem.batch_id,
            self.name,
            self.version,
            tuple(assignments),
            tuple(unassigned),
            total_cost,
            (perf_counter() - started) * 1000,
        )
