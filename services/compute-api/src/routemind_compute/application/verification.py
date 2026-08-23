from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Protocol

from routemind_compute.application.nearest import great_circle_distance_kilometres
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


def _finite(value: object) -> bool:
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
