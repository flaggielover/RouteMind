from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite
from typing import Any, Protocol, TypeGuard

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.application.public_benchmarks import (
    CanonicalVrptwInstance,
    CanonicalVrptwNode,
    PublicVrptwRoute,
    PublicVrptwSolution,
)
from routemind_compute.application.vrptw import VrpProblem, VrpRoutePlan
from routemind_compute.domain.dispatch import CourierCandidate, DispatchDecision, DispatchProblem


class _TravelProvider(Protocol):
    def estimate(self, origin: Any, destination: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class VerificationIssue:
    code: str
    message: str
    subject: str = ""

    def as_dict(self) -> dict[str, str]:
        result = {"code": self.code, "message": self.message}
        if self.subject:
            result["subject"] = self.subject
        return result


@dataclass(frozen=True, slots=True)
class VerificationReport:
    valid: bool
    issues: tuple[VerificationIssue, ...] = ()
    checks: tuple[str, ...] = ()

    @classmethod
    def from_issues(
        cls, issues: list[VerificationIssue], checks: tuple[str, ...]
    ) -> VerificationReport:
        return cls(not issues, tuple(issues), checks)


@dataclass(frozen=True, slots=True)
class PublicVrptwVerificationReport:
    valid: bool
    issues: tuple[VerificationIssue, ...]
    checks: tuple[str, ...]
    recomputed_vehicle_count: int
    recomputed_total_distance: float
    complete: bool


class SolverOutputInvalidError(ValueError):
    """Raised when a strategy result fails the independent verification boundary."""

    def __init__(self, report: VerificationReport) -> None:
        self.report = report
        summary = "; ".join(issue.code for issue in report.issues) or "unknown"
        super().__init__(f"solver output failed verification: {summary}")

    def as_detail(self) -> dict[str, object]:
        return {
            "code": "solver_output_invalid",
            "message": "solver output failed independent verification",
            "reasons": tuple(issue.as_dict() for issue in self.report.issues),
            "checks": self.report.checks,
        }


def _finite(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _candidate_constraints(
    problem: DispatchProblem, candidate: CourierCandidate
) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    subject = candidate.courier_id
    if candidate.state != "available":
        issues.append(
            VerificationIssue("courier_unavailable", f"courier state is {candidate.state}", subject)
        )
    if candidate.capacity_units - candidate.current_load_units + 1e-9 < problem.demand_units:
        issues.append(
            VerificationIssue("capacity_violation", "remaining capacity is below demand", subject)
        )
    if candidate.service_risk > problem.max_service_risk + 1e-9:
        issues.append(
            VerificationIssue(
                "service_risk_violation", "service risk exceeds problem limit", subject
            )
        )
    if not _finite(candidate.estimated_travel_seconds) or candidate.estimated_travel_seconds < 0:
        issues.append(
            VerificationIssue("travel_time_invalid", "estimated travel time is invalid", subject)
        )
        return issues
    service_start = max(problem.pickup_ready_at_seconds, candidate.available_from_seconds)
    delivery_at = service_start + candidate.estimated_travel_seconds + problem.service_seconds
    if problem.delivery_window is not None:
        delivery_at = max(delivery_at, problem.delivery_window.start_seconds)
        if delivery_at > problem.delivery_window.end_seconds + 1e-9:
            issues.append(
                VerificationIssue("time_window_violation", "delivery window is missed", subject)
            )
    if (
        candidate.available_until_seconds is not None
        and delivery_at > candidate.available_until_seconds + 1e-9
    ):
        issues.append(
            VerificationIssue(
                "availability_window_violation", "courier availability ends too early", subject
            )
        )
    return issues


def _expected_dispatch_score(
    problem: DispatchProblem, decision: DispatchDecision, strategy: object
) -> float | None:
    if decision.courier_id is None:
        return None
    candidate = next(item for item in problem.candidates if item.courier_id == decision.courier_id)
    distance = great_circle_distance_kilometres(
        problem.pickup.latitude,
        problem.pickup.longitude,
        candidate.location.latitude,
        candidate.location.longitude,
    )
    if decision.strategy in {"nearest", "hungarian", "minimum-cost-flow", "partitioned-assignment"}:
        return distance
    if decision.strategy == "weighted-greedy":
        weight = getattr(strategy, "distance_weight", 1.0)
        return distance * float(weight) if _finite(weight) else None
    if decision.strategy == "risk-aware":
        weights = getattr(strategy, "weights_tuple", None)
        if not isinstance(weights, tuple) or len(weights) != 5:
            return None
        components = (
            distance,
            max(0.0, candidate.available_from_seconds - problem.pickup_ready_at_seconds) / 60.0,
            candidate.overtime_risk,
            candidate.service_risk,
            candidate.current_load_units / candidate.capacity_units,
        )
        return sum(
            float(weight) * component for weight, component in zip(weights, components, strict=True)
        )
    if decision.strategy == "vrptw":
        # The single-request adapter's authoritative objective is the planner's
        # route value; the metadata projection is intentionally rounded.  Full
        # route plans are checked by verify_vrptw_plan below.
        return None
    return None


def verify_dispatch_decision(
    problem: DispatchProblem, decision: DispatchDecision, strategy: object
) -> VerificationReport:
    """Verify a single-request result without calling DispatchProblem's solver predicate."""
    issues: list[VerificationIssue] = []
    checks = ("membership", "capacity", "time_windows", "travel", "feasibility", "objective")
    if decision.request_id != problem.request_id:
        issues.append(
            VerificationIssue("request_mismatch", "decision request does not match problem")
        )
    if decision.courier_id is None:
        if _independent_eligible(problem):
            issues.append(
                VerificationIssue(
                    "unassigned_feasible", "decision is unassigned despite an eligible courier"
                )
            )
    else:
        candidate = next(
            (item for item in problem.candidates if item.courier_id == decision.courier_id), None
        )
        if candidate is None:
            issues.append(
                VerificationIssue(
                    "membership_violation",
                    "selected courier is not in the candidate set",
                    decision.courier_id,
                )
            )
        else:
            issues.extend(_candidate_constraints(problem, candidate))
            if decision.score is None or not _finite(decision.score) or decision.score < 0:
                issues.append(
                    VerificationIssue(
                        "objective_invalid",
                        "assigned decision score must be finite and non-negative",
                    )
                )
            expected = _expected_dispatch_score(problem, decision, strategy)
            if expected is not None and decision.score is not None:
                tolerance = max(1e-6, abs(expected) * 1e-9)
                if abs(decision.score - expected) > tolerance:
                    issues.append(
                        VerificationIssue(
                            "objective_mismatch",
                            f"claimed score {decision.score} differs from recomputed {expected}",
                        )
                    )
    return VerificationReport.from_issues(issues, checks)


def _independent_eligible(problem: DispatchProblem) -> bool:
    return any(not _candidate_constraints(problem, candidate) for candidate in problem.candidates)


def _travel_seconds(provider: _TravelProvider, origin: Any, destination: Any) -> float | None:
    try:
        value = provider.estimate(origin, destination)
        seconds = getattr(value, "seconds", None)
    except Exception:
        return None
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
        return None
    if not isfinite(seconds) or seconds < 0:
        return None
    return float(seconds)


def verify_vrptw_plan(
    problem: VrpProblem, plan: VrpRoutePlan, travel_provider: _TravelProvider
) -> VerificationReport:
    """Independently recompute every route's timing, load, travel, and objective."""
    issues: list[VerificationIssue] = []
    checks = (
        "stop_uniqueness",
        "route_membership",
        "vehicle_existence",
        "capacity",
        "time_windows",
        "service_time",
        "vehicle_availability",
        "return_constraints",
        "unassigned_semantics",
        "objective_recomputation",
        "route_travel_time",
        "feasibility",
    )
    if plan.problem_id != problem.problem_id:
        issues.append(
            VerificationIssue("problem_mismatch", "route plan problem does not match input")
        )
    stop_by_id = {stop.stop_id: stop for stop in problem.stops}
    vehicle_by_id = {vehicle.vehicle_id: vehicle for vehicle in problem.vehicles}
    routed: list[str] = []
    route_vehicle_ids: set[str] = set()
    recomputed_total = 0.0
    for route in plan.routes:
        subject = route.vehicle_id
        if subject in route_vehicle_ids:
            issues.append(
                VerificationIssue("vehicle_duplicate", "vehicle has more than one route", subject)
            )
        route_vehicle_ids.add(subject)
        vehicle = vehicle_by_id.get(subject)
        if vehicle is None:
            issues.append(
                VerificationIssue("vehicle_missing", "route references an unknown vehicle", subject)
            )
            continue
        lengths = {
            len(route.stop_ids),
            len(route.arrival_seconds),
            len(route.service_start_seconds),
            len(route.departure_seconds),
        }
        if len(lengths) != 1:
            issues.append(
                VerificationIssue(
                    "route_shape_invalid",
                    "route timing arrays do not match stop membership",
                    subject,
                )
            )
            continue
        current = vehicle.start_location
        clock = vehicle.available_from_seconds
        load = 0.0
        travel = 0.0
        for index, stop_id in enumerate(route.stop_ids):
            if stop_id not in stop_by_id:
                issues.append(
                    VerificationIssue("stop_missing", "route references an unknown stop", stop_id)
                )
                continue
            if stop_id in routed:
                issues.append(
                    VerificationIssue(
                        "stop_duplicate", "stop appears in more than one route", stop_id
                    )
                )
            routed.append(stop_id)
            stop = stop_by_id[stop_id]
            load += stop.demand_units
            leg = _travel_seconds(travel_provider, current, stop.location)
            if leg is None:
                issues.append(
                    VerificationIssue(
                        "travel_invalid", "travel provider returned an invalid leg", stop_id
                    )
                )
                continue
            travel += leg
            arrival = clock + leg
            service_start = max(
                arrival, stop.time_window.start_seconds if stop.time_window else 0.0
            )
            departure = service_start + stop.service_seconds
            for value, name in (
                (route.arrival_seconds[index], "arrival"),
                (route.service_start_seconds[index], "service_start"),
                (route.departure_seconds[index], "departure"),
            ):
                if not _finite(value) or float(value) < 0:
                    issues.append(
                        VerificationIssue("timing_invalid", f"reported {name} is invalid", stop_id)
                    )
            if abs(route.arrival_seconds[index] - arrival) > 1e-6:
                issues.append(
                    VerificationIssue(
                        "arrival_mismatch", "reported arrival differs from recomputation", stop_id
                    )
                )
            if abs(route.service_start_seconds[index] - service_start) > 1e-6:
                issues.append(
                    VerificationIssue(
                        "service_start_mismatch",
                        "reported service start differs from recomputation",
                        stop_id,
                    )
                )
            if abs(route.departure_seconds[index] - departure) > 1e-6:
                issues.append(
                    VerificationIssue(
                        "service_time_mismatch",
                        "reported departure differs from recomputation",
                        stop_id,
                    )
                )
            if stop.time_window is not None and service_start > stop.time_window.end_seconds + 1e-9:
                issues.append(
                    VerificationIssue(
                        "time_window_violation", "route misses stop time window", stop_id
                    )
                )
            if (
                vehicle.available_until_seconds is not None
                and departure > vehicle.available_until_seconds + 1e-9
            ):
                issues.append(
                    VerificationIssue(
                        "availability_window_violation",
                        "route exceeds vehicle availability",
                        subject,
                    )
                )
            current, clock = stop.location, departure
        if load > vehicle.capacity_units + 1e-9:
            issues.append(
                VerificationIssue(
                    "capacity_violation", "route load exceeds vehicle capacity", subject
                )
            )
        if problem.return_to_depot and route.stop_ids:
            leg = _travel_seconds(travel_provider, current, problem.depot)
            if leg is None:
                issues.append(
                    VerificationIssue(
                        "return_travel_invalid", "return-to-depot travel is invalid", subject
                    )
                )
            else:
                travel += leg
                clock += leg
                if (
                    vehicle.available_until_seconds is not None
                    and clock > vehicle.available_until_seconds + 1e-9
                ):
                    issues.append(
                        VerificationIssue(
                            "return_availability_violation",
                            "return exceeds vehicle availability",
                            subject,
                        )
                    )
        if not _finite(route.load_units) or abs(route.load_units - load) > 1e-6:
            issues.append(
                VerificationIssue(
                    "load_mismatch", "reported route load differs from recomputation", subject
                )
            )
        if not _finite(route.travel_seconds) or abs(route.travel_seconds - travel) > 1e-6:
            issues.append(
                VerificationIssue(
                    "travel_mismatch", "reported route travel differs from recomputation", subject
                )
            )
        if not _finite(route.completion_seconds) or abs(route.completion_seconds - clock) > 1e-6:
            issues.append(
                VerificationIssue(
                    "completion_mismatch", "reported completion differs from recomputation", subject
                )
            )
        recomputed_total += travel
    unassigned_ids = [stop_id for stop_id, reason in plan.unassigned]
    if len(unassigned_ids) != len(set(unassigned_ids)):
        issues.append(
            VerificationIssue("unassigned_duplicate", "unassigned stop appears more than once")
        )
    if any(stop_id not in stop_by_id for stop_id in unassigned_ids):
        issues.append(
            VerificationIssue("unassigned_unknown", "unassigned list references an unknown stop")
        )
    if any(not reason.strip() for _, reason in plan.unassigned):
        issues.append(
            VerificationIssue("unassigned_reason_missing", "unassigned stop must include a reason")
        )
    if set(routed).intersection(unassigned_ids):
        issues.append(
            VerificationIssue("assignment_overlap", "a stop is both routed and unassigned")
        )
    if set(routed).union(unassigned_ids) != set(stop_by_id):
        issues.append(
            VerificationIssue(
                "unassigned_semantics", "every input stop must be routed or explicitly unassigned"
            )
        )
    if (
        not _finite(plan.total_travel_seconds)
        or abs(plan.total_travel_seconds - recomputed_total) > 1e-6
    ):
        issues.append(
            VerificationIssue("objective_mismatch", "plan objective differs from recomputed travel")
        )
    return VerificationReport.from_issues(issues, checks)


def verify_public_vrptw_solution(
    instance: CanonicalVrptwInstance,
    solution: PublicVrptwSolution,
    *,
    require_complete: bool = True,
    tolerance: float = 1e-6,
) -> PublicVrptwVerificationReport:
    """Recompute a public VRPTW result without calling or trusting the solver."""
    checks = (
        "instance_identity",
        "depot_start_end",
        "route_continuity",
        "vehicle_identity_and_count",
        "node_membership_and_uniqueness",
        "service_timing",
        "capacity",
        "time_windows",
        "unassigned_policy",
        "objective_recomputation",
        "feasibility_claim",
        "precedence_not_applicable_to_canonical_vrptw_v1",
    )
    issues: list[VerificationIssue] = []
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("verification tolerance must be finite and positive")
    if solution.instance_id != instance.instance_id:
        issues.append(
            VerificationIssue(
                "instance_mismatch", "solution instance does not match canonical input"
            )
        )
    if solution.objective_semantics != instance.objective_semantics:
        issues.append(
            VerificationIssue(
                "objective_semantics_mismatch",
                "solution objective semantics do not match canonical input",
            )
        )

    node_by_id = {instance.depot.node_id: instance.depot}
    node_by_id.update({item.node_id: item for item in instance.customers})
    customer_ids = {item.node_id for item in instance.customers}
    routed: list[int] = []
    vehicle_ids: list[str] = []
    total_distance = 0.0
    for route in solution.routes:
        vehicle_ids.append(route.vehicle_id)
        route_distance = _verify_public_route(
            instance, route, node_by_id, routed, issues, tolerance
        )
        total_distance += route_distance
    if any(not vehicle_id.strip() for vehicle_id in vehicle_ids):
        issues.append(
            VerificationIssue("vehicle_id_blank", "vehicle identifiers must not be blank")
        )
    if len(vehicle_ids) != len(set(vehicle_ids)):
        issues.append(
            VerificationIssue("vehicle_duplicate", "a vehicle has more than one public route")
        )
    vehicle_count = len(solution.routes)
    if vehicle_count > instance.max_vehicles:
        issues.append(
            VerificationIssue(
                "vehicle_limit_exceeded", "solution uses more than the maximum vehicle count"
            )
        )
    if (
        not isinstance(solution.claimed_vehicle_count, int)
        or isinstance(solution.claimed_vehicle_count, bool)
        or solution.claimed_vehicle_count != vehicle_count
    ):
        issues.append(
            VerificationIssue(
                "vehicle_count_mismatch", "claimed vehicle count differs from route count"
            )
        )

    unassigned = list(solution.unassigned_node_ids)
    if len(unassigned) != len(set(unassigned)):
        issues.append(
            VerificationIssue("unassigned_duplicate", "unassigned customer appears more than once")
        )
    if any(node_id not in customer_ids for node_id in unassigned):
        issues.append(
            VerificationIssue(
                "unassigned_unknown", "unassigned list contains an unknown or depot node"
            )
        )
    if set(routed).intersection(unassigned):
        issues.append(
            VerificationIssue("assignment_overlap", "a customer is both routed and unassigned")
        )
    covered = set(routed).union(unassigned)
    complete = covered == customer_ids and not unassigned
    if covered != customer_ids:
        issues.append(
            VerificationIssue(
                "customer_coverage_incomplete",
                "every customer must be routed or explicitly unassigned",
            )
        )
    if require_complete and unassigned:
        issues.append(
            VerificationIssue(
                "unassigned_not_allowed", "verification policy requires a complete solution"
            )
        )
    if (
        not _finite(solution.claimed_total_distance)
        or abs(solution.claimed_total_distance - total_distance) > tolerance
    ):
        issues.append(
            VerificationIssue(
                "total_distance_mismatch",
                "claimed total distance differs from independent recomputation",
            )
        )

    semantic_issues = bool(issues)
    if not isinstance(solution.claimed_feasible, bool):
        issues.append(
            VerificationIssue("feasibility_claim_invalid", "claimed_feasible must be boolean")
        )
    elif solution.claimed_feasible == semantic_issues:
        issues.append(
            VerificationIssue(
                "feasibility_claim_mismatch",
                "solver feasibility claim differs from independent verification",
            )
        )
    return PublicVrptwVerificationReport(
        valid=not issues,
        issues=tuple(issues),
        checks=checks,
        recomputed_vehicle_count=vehicle_count,
        recomputed_total_distance=total_distance,
        complete=complete,
    )


def _verify_public_route(
    instance: CanonicalVrptwInstance,
    route: PublicVrptwRoute,
    node_by_id: dict[int, CanonicalVrptwNode],
    routed: list[int],
    issues: list[VerificationIssue],
    tolerance: float,
) -> float:
    subject = route.vehicle_id
    if len(route.visits) < 2:
        issues.append(
            VerificationIssue(
                "route_shape_invalid", "route must include start and end depot visits", subject
            )
        )
        return 0.0
    if route.visits[0].node_id != instance.depot.node_id:
        issues.append(
            VerificationIssue("route_start_not_depot", "route must start at depot", subject)
        )
    if route.visits[-1].node_id != instance.depot.node_id:
        issues.append(
            VerificationIssue("route_end_not_depot", "route must return to depot", subject)
        )
    if any(visit.node_id == instance.depot.node_id for visit in route.visits[1:-1]):
        issues.append(
            VerificationIssue("interior_depot", "depot cannot appear inside a route", subject)
        )

    route_distance = 0.0
    route_load = 0.0
    previous: CanonicalVrptwNode | None = None
    previous_departure: float | None = None
    for index, visit in enumerate(route.visits):
        node = node_by_id.get(visit.node_id)
        if node is None:
            issues.append(
                VerificationIssue(
                    "route_node_unknown",
                    "route contains a node outside the instance",
                    str(visit.node_id),
                )
            )
            previous = None
            previous_departure = None
            continue
        _verify_public_visit_timing(
            node,
            visit.arrival_time,
            visit.service_start_time,
            visit.departure_time,
            previous,
            previous_departure,
            issues,
            tolerance,
        )
        if previous is not None:
            route_distance += hypot(
                node.point.x - previous.point.x, node.point.y - previous.point.y
            )
        if index not in {0, len(route.visits) - 1} and node.node_id != instance.depot.node_id:
            if node.node_id in routed:
                issues.append(
                    VerificationIssue(
                        "customer_duplicate", "customer appears more than once", str(node.node_id)
                    )
                )
            routed.append(node.node_id)
            route_load += node.demand
        previous = node
        previous_departure = float(visit.departure_time) if _finite(visit.departure_time) else None
    if route_load > instance.vehicle_capacity + tolerance:
        issues.append(
            VerificationIssue(
                "capacity_violation", "route demand exceeds vehicle capacity", subject
            )
        )
    if (
        not _finite(route.claimed_distance)
        or abs(route.claimed_distance - route_distance) > tolerance
    ):
        issues.append(
            VerificationIssue(
                "route_distance_mismatch",
                "claimed route distance differs from independent recomputation",
                subject,
            )
        )
    return route_distance


def _verify_public_visit_timing(
    node: CanonicalVrptwNode,
    arrival: object,
    service_start: object,
    departure: object,
    previous: CanonicalVrptwNode | None,
    previous_departure: float | None,
    issues: list[VerificationIssue],
    tolerance: float,
) -> None:
    subject = str(node.node_id)
    if (
        not _finite(arrival)
        or arrival < 0
        or not _finite(service_start)
        or service_start < 0
        or not _finite(departure)
        or departure < 0
    ):
        issues.append(
            VerificationIssue(
                "timing_invalid", "visit timing must be finite and non-negative", subject
            )
        )
        return
    reported_arrival = float(arrival)
    reported_service = float(service_start)
    reported_departure = float(departure)
    if previous is None:
        expected_arrival = node.ready_time
        if abs(reported_arrival - expected_arrival) > tolerance:
            issues.append(
                VerificationIssue(
                    "arrival_mismatch", "reported timing differs from recomputation", subject
                )
            )
        if reported_service + tolerance < max(reported_arrival, node.ready_time):
            issues.append(
                VerificationIssue(
                    "service_start_mismatch",
                    "service starts before arrival or ready time",
                    subject,
                )
            )
        expected_departure = reported_service + node.service_time
        if abs(reported_departure - expected_departure) > tolerance:
            issues.append(
                VerificationIssue(
                    "departure_mismatch", "reported timing differs from recomputation", subject
                )
            )
    elif previous_departure is None:
        issues.append(
            VerificationIssue(
                "route_continuity_invalid", "previous departure is unavailable", subject
            )
        )
        return
    else:
        expected_arrival = previous_departure + hypot(
            node.point.x - previous.point.x, node.point.y - previous.point.y
        )
        earliest_service = max(reported_arrival, node.ready_time)
        if abs(reported_arrival - expected_arrival) > tolerance:
            issues.append(
                VerificationIssue(
                    "arrival_mismatch", "reported timing differs from recomputation", subject
                )
            )
        if reported_service + tolerance < earliest_service:
            issues.append(
                VerificationIssue(
                    "service_start_mismatch",
                    "service starts before arrival or ready time",
                    subject,
                )
            )
        expected_departure = reported_service + node.service_time
        if abs(reported_departure - expected_departure) > tolerance:
            issues.append(
                VerificationIssue(
                    "departure_mismatch", "reported timing differs from recomputation", subject
                )
            )
    if reported_service > node.due_time + tolerance:
        issues.append(
            VerificationIssue("time_window_violation", "service starts after due time", subject)
        )
