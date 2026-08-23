from dataclasses import replace
from types import SimpleNamespace

import pytest

from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.application.verification import (
    SolverOutputInvalidError,
    VerificationIssue,
    VerificationReport,
    _travel_seconds,
    verify_dispatch_decision,
    verify_vrptw_plan,
)
from routemind_compute.application.vrptw import (
    VrpProblem,
    VrpRoute,
    VrpRoutePlan,
    VrpStop,
    VrptwRoutePlanner,
    VrptwStrategy,
    VrpVehicle,
)
from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchDecision,
    DispatchProblem,
    GeoPoint,
    TimeWindow,
)


def dispatch_problem() -> DispatchProblem:
    return DispatchProblem(
        "verify-request",
        GeoPoint(0, 0),
        (
            CourierCandidate(
                "courier", GeoPoint(0, 0.01), capacity_units=2, estimated_travel_seconds=10
            ),
        ),
        demand_units=1,
        service_seconds=5,
        delivery_window=TimeWindow(0, 100),
    )


def test_registry_rejects_invalid_solver_output_with_structured_reasons() -> None:
    class BrokenStrategy:
        name = "broken"
        version = "1.0.0"

        def solve(self, problem: DispatchProblem) -> DispatchDecision:
            return DispatchDecision(problem.request_id, self.name, "missing", 1.0)

    with pytest.raises(SolverOutputInvalidError) as raised:
        StrategyRegistry((BrokenStrategy(),)).solve("broken", dispatch_problem())
    assert raised.value.report.valid is False
    assert raised.value.report.issues[0].code == "membership_violation"
    assert raised.value.as_detail()["code"] == "solver_output_invalid"


def test_dispatch_verifier_checks_constraints_and_objective_independently() -> None:
    problem = dispatch_problem()
    valid = NearestStrategy().solve(problem)
    assert verify_dispatch_decision(problem, valid, NearestStrategy()).valid is True

    invalid = replace(valid, courier_id="courier", score=999.0)
    report = verify_dispatch_decision(problem, invalid, NearestStrategy())
    assert report.valid is False
    assert {issue.code for issue in report.issues} == {"objective_mismatch"}

    blocked = replace(problem, demand_units=3)
    blocked_decision = DispatchDecision(blocked.request_id, "nearest", None, None)
    assert verify_dispatch_decision(blocked, blocked_decision, NearestStrategy()).valid is True


def test_vrptw_verifier_recomputes_route_and_detects_tampering() -> None:
    point = GeoPoint(0, 0)
    problem = VrpProblem(
        "vrp-verify",
        point,
        (VrpStop("stop", GeoPoint(0, 0.01), service_seconds=5),),
        (VrpVehicle("vehicle", point, 2),),
        return_to_depot=True,
    )
    provider = DeterministicLocalTravelProvider()
    plan = VrptwRoutePlanner(provider).plan(problem)
    assert verify_vrptw_plan(problem, plan, provider).valid is True

    route = plan.routes[0]
    tampered = VrpRoute(
        route.vehicle_id,
        route.stop_ids,
        route.arrival_seconds,
        route.service_start_seconds,
        route.departure_seconds,
        route.load_units,
        route.travel_seconds + 1,
        route.completion_seconds,
    )
    invalid = VrpRoutePlan(plan.problem_id, (tampered,), (), tampered.travel_seconds)
    report = verify_vrptw_plan(problem, invalid, provider)
    assert report.valid is False
    assert any(issue.code == "travel_mismatch" for issue in report.issues)


def test_vrptw_verifier_requires_explicit_unassigned_semantics() -> None:
    point = GeoPoint(0, 0)
    problem = VrpProblem(
        "vrp-unassigned",
        point,
        (VrpStop("stop", point),),
        (VrpVehicle("vehicle", point, 1),),
        return_to_depot=False,
    )
    empty = VrpRoutePlan("vrp-unassigned", (), (), 0.0)
    report = verify_vrptw_plan(problem, empty, DeterministicLocalTravelProvider())
    assert report.valid is False
    assert any(issue.code == "unassigned_semantics" for issue in report.issues)


def test_default_registry_exposes_honest_maturity_labels() -> None:
    descriptors = {item.name: item for item in default_registry().descriptors()}
    assert descriptors["nearest"].maturity == "BASELINE"
    assert descriptors["minimum-cost-flow"].maturity == "ENGINEERING"
    assert descriptors["vrptw"].maturity == "BASELINE"


def test_dispatch_verifier_reports_all_independent_constraint_failures() -> None:
    problem = replace(
        dispatch_problem(),
        demand_units=3,
        max_service_risk=0.1,
        delivery_window=TimeWindow(0, 1),
    )
    candidate = replace(
        problem.candidates[0],
        state="offline",
        service_risk=0.9,
        available_until_seconds=1,
    )
    problem = replace(problem, candidates=(candidate,))
    decision = DispatchDecision(problem.request_id, "nearest", candidate.courier_id, None)
    report = verify_dispatch_decision(problem, decision, NearestStrategy())
    assert {issue.code for issue in report.issues} == {
        "courier_unavailable",
        "capacity_violation",
        "service_risk_violation",
        "time_window_violation",
        "availability_window_violation",
        "objective_invalid",
    }
    eligible = DispatchDecision(problem.request_id, "nearest", None, None)
    assert verify_dispatch_decision(problem, eligible, NearestStrategy()).valid is True


def test_dispatch_verifier_covers_objective_adapters_and_identity() -> None:
    problem = dispatch_problem()
    nearest = NearestStrategy().solve(problem)
    mismatched = replace(nearest, request_id="other")
    assert any(
        item.code == "request_mismatch"
        for item in verify_dispatch_decision(problem, mismatched, NearestStrategy()).issues
    )
    weighted = replace(nearest, strategy="weighted-greedy", score=nearest.score)
    assert verify_dispatch_decision(problem, weighted, SimpleNamespace(distance_weight=1.0)).valid
    risk = replace(nearest, strategy="risk-aware", score=nearest.score)
    assert not verify_dispatch_decision(
        problem, risk, SimpleNamespace(weights_tuple=(2, 0, 0, 0, 0))
    ).valid
    unknown = replace(nearest, strategy="external")
    assert verify_dispatch_decision(problem, unknown, object()).valid
    issue = VerificationIssue("code", "message", "subject")
    assert issue.as_dict()["subject"] == "subject"
    assert SolverOutputInvalidError(VerificationReport(True)).as_detail()["reasons"] == ()


def test_travel_verification_rejects_provider_failures() -> None:
    class Raises:
        def estimate(self, origin: object, destination: object) -> object:
            raise RuntimeError("unavailable")

    class Invalid:
        def __init__(self, value: object) -> None:
            self.value = value

        def estimate(self, origin: object, destination: object) -> object:
            return SimpleNamespace(seconds=self.value)

    assert _travel_seconds(Raises(), object(), object()) is None
    assert _travel_seconds(Invalid("bad"), object(), object()) is None
    assert _travel_seconds(Invalid(float("nan")), object(), object()) is None
    assert _travel_seconds(Invalid(-1), object(), object()) is None


def test_vrptw_verifier_reports_membership_timing_capacity_and_unassigned_failures() -> None:
    point = GeoPoint(0, 0)
    stop = VrpStop(
        "stop", GeoPoint(0, 0.01), demand_units=2, service_seconds=5, time_window=TimeWindow(0, 1)
    )
    problem = VrpProblem(
        "vrp-invalid",
        point,
        (stop,),
        (VrpVehicle("vehicle", point, 1, available_until_seconds=1),),
        return_to_depot=True,
    )
    route = VrpRoute("vehicle", ("stop",), (float("nan"),), (0,), (0,), 0, 0, 0)
    duplicate_vehicle = VrpRoute("vehicle", (), (), (), (), 0, 0, 0)
    unknown = VrpRoute("missing", ("unknown",), (0,), (0,), (0,), 0, 0, 0)
    plan = VrpRoutePlan(
        "other",
        (route, duplicate_vehicle, unknown),
        (("stop", ""), ("stop", "duplicate"), ("unknown", "reason")),
        99,
    )
    report = verify_vrptw_plan(problem, plan, DeterministicLocalTravelProvider())
    codes = {issue.code for issue in report.issues}
    assert {
        "problem_mismatch",
        "vehicle_duplicate",
        "timing_invalid",
        "time_window_violation",
        "capacity_violation",
        "return_availability_violation",
        "load_mismatch",
        "travel_mismatch",
        "completion_mismatch",
        "vehicle_missing",
        "unassigned_duplicate",
        "unassigned_reason_missing",
        "assignment_overlap",
        "objective_mismatch",
    }.issubset(codes)


def test_vrptw_verifier_handles_invalid_route_shapes_and_travel() -> None:
    point = GeoPoint(0, 0)
    problem = VrpProblem(
        "vrp-shape", point, (VrpStop("stop", point),), (VrpVehicle("vehicle", point, 1),)
    )
    malformed = VrpRoute("vehicle", ("stop",), (), (), (), 1, 0, 0)
    plan = VrpRoutePlan("vrp-shape", (malformed,), (), 0)
    assert any(
        issue.code == "route_shape_invalid"
        for issue in verify_vrptw_plan(problem, plan, DeterministicLocalTravelProvider()).issues
    )

    class InvalidProvider:
        def estimate(self, origin: object, destination: object) -> object:
            return SimpleNamespace(seconds=float("nan"))

    route = VrpRoute("vehicle", ("stop",), (0,), (0,), (0,), 1, 0, 0)
    invalid = VrpRoutePlan("vrp-shape", (route,), (), 0)
    assert any(
        issue.code == "travel_invalid"
        for issue in verify_vrptw_plan(problem, invalid, InvalidProvider()).issues
    )


def test_vrptw_strategy_rejects_invalid_planner_output_before_adaptation() -> None:
    provider = DeterministicLocalTravelProvider()

    class BrokenPlanner:
        travel_provider = provider

        def plan(self, problem: VrpProblem) -> VrpRoutePlan:
            return VrpRoutePlan(problem.problem_id, (), (), 0.0)

    with pytest.raises(SolverOutputInvalidError) as raised:
        VrptwStrategy(BrokenPlanner()).solve(dispatch_problem())  # type: ignore[arg-type]
    assert any(issue.code == "unassigned_semantics" for issue in raised.value.report.issues)
