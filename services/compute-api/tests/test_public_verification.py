from __future__ import annotations

from dataclasses import replace

import pytest

from routemind_compute.application.public_benchmarks import (
    CanonicalVrptwInstance,
    CanonicalVrptwNode,
    CartesianPoint,
    PublicVrptwRoute,
    PublicVrptwSolution,
    PublicVrptwVisit,
)
from routemind_compute.application.verification import (
    PublicVrptwVerificationReport,
    verify_public_vrptw_solution,
)


def node(
    node_id: int,
    x: float,
    y: float,
    demand: float,
    ready: float,
    due: float,
    service: float,
) -> CanonicalVrptwNode:
    return CanonicalVrptwNode(
        node_id,
        CartesianPoint(x, y),
        demand,
        ready,
        due,
        service,
    )


def instance_for(**overrides: object) -> CanonicalVrptwInstance:
    values: dict[str, object] = {
        "instance_id": "TINY101",
        "max_vehicles": 2,
        "vehicle_capacity": 10,
        "depot": node(0, 0, 0, 0, 0, 100, 0),
        "customers": (
            node(1, 3, 4, 4, 0, 50, 5),
            node(2, 6, 8, 5, 10, 80, 5),
        ),
    }
    values.update(overrides)
    return CanonicalVrptwInstance(**values)  # type: ignore[arg-type]


def valid_route(**overrides: object) -> PublicVrptwRoute:
    values: dict[str, object] = {
        "vehicle_id": "vehicle-1",
        "visits": (
            PublicVrptwVisit(0, 0, 0, 0),
            PublicVrptwVisit(1, 5, 5, 10),
            PublicVrptwVisit(2, 15, 15, 20),
            PublicVrptwVisit(0, 30, 30, 30),
        ),
        "claimed_distance": 20,
    }
    values.update(overrides)
    return PublicVrptwRoute(**values)  # type: ignore[arg-type]


def solution_for(**overrides: object) -> PublicVrptwSolution:
    values: dict[str, object] = {
        "instance_id": "TINY101",
        "routes": (valid_route(),),
        "unassigned_node_ids": (),
        "claimed_vehicle_count": 1,
        "claimed_total_distance": 20,
        "claimed_feasible": True,
        "objective_semantics": "HIERARCHICAL_VEHICLES_THEN_DISTANCE",
    }
    values.update(overrides)
    return PublicVrptwSolution(**values)  # type: ignore[arg-type]


def issue_codes(report: PublicVrptwVerificationReport) -> set[str]:
    return {item.code for item in report.issues}


def test_independent_public_verifier_accepts_complete_recomputed_solution() -> None:
    report = verify_public_vrptw_solution(instance_for(), solution_for())

    assert report.valid is True
    assert report.issues == ()
    assert report.complete is True
    assert report.recomputed_vehicle_count == 1
    assert report.recomputed_total_distance == pytest.approx(20)
    assert "precedence_not_applicable_to_canonical_vrptw_v1" in report.checks


def test_verifier_allows_explicit_wait_at_start_depot() -> None:
    route = valid_route(
        visits=(
            PublicVrptwVisit(0, 0, 2, 2),
            PublicVrptwVisit(1, 7, 7, 12),
            PublicVrptwVisit(2, 17, 17, 22),
            PublicVrptwVisit(0, 32, 32, 32),
        )
    )

    report = verify_public_vrptw_solution(instance_for(), solution_for(routes=(route,)))

    assert report.valid is True


def test_verifier_allows_feasible_wait_at_customer() -> None:
    route = valid_route(
        visits=(
            PublicVrptwVisit(0, 0, 0, 0),
            PublicVrptwVisit(1, 5, 7, 12),
            PublicVrptwVisit(2, 17, 17, 22),
            PublicVrptwVisit(0, 32, 32, 32),
        )
    )

    report = verify_public_vrptw_solution(instance_for(), solution_for(routes=(route,)))

    assert report.valid is True


@pytest.mark.parametrize(
    "solution, expected",
    [
        (solution_for(instance_id="OTHER"), "instance_mismatch"),
        (solution_for(objective_semantics="MONOLITHIC_DISTANCE"), "objective_semantics_mismatch"),
        (solution_for(claimed_vehicle_count=2), "vehicle_count_mismatch"),
        (solution_for(claimed_vehicle_count=True), "vehicle_count_mismatch"),
        (solution_for(claimed_vehicle_count=1.0), "vehicle_count_mismatch"),
        (solution_for(claimed_total_distance=19), "total_distance_mismatch"),
        (solution_for(claimed_total_distance=float("nan")), "total_distance_mismatch"),
        (solution_for(claimed_feasible=False), "feasibility_claim_mismatch"),
        (solution_for(claimed_feasible=1), "feasibility_claim_invalid"),
    ],
)
def test_verifier_rejects_untrusted_solution_claims(
    solution: PublicVrptwSolution, expected: str
) -> None:
    report = verify_public_vrptw_solution(instance_for(), solution)

    assert report.valid is False
    assert expected in issue_codes(report)


@pytest.mark.parametrize(
    "route, expected",
    [
        (valid_route(vehicle_id=" "), "vehicle_id_blank"),
        (valid_route(visits=()), "route_shape_invalid"),
        (
            valid_route(visits=valid_route().visits[1:]),
            "route_start_not_depot",
        ),
        (
            valid_route(visits=valid_route().visits[:-1]),
            "route_end_not_depot",
        ),
        (
            valid_route(
                visits=(
                    PublicVrptwVisit(0, 0, 0, 0),
                    PublicVrptwVisit(0, 0, 0, 0),
                    *valid_route().visits[1:],
                )
            ),
            "interior_depot",
        ),
        (
            valid_route(
                visits=(
                    PublicVrptwVisit(0, 0, 0, 0),
                    PublicVrptwVisit(99, 1, 1, 1),
                    PublicVrptwVisit(0, 2, 2, 2),
                )
            ),
            "route_node_unknown",
        ),
        (valid_route(claimed_distance=21), "route_distance_mismatch"),
        (valid_route(claimed_distance=float("inf")), "route_distance_mismatch"),
    ],
)
def test_verifier_rejects_route_shape_membership_and_distance(
    route: PublicVrptwRoute, expected: str
) -> None:
    report = verify_public_vrptw_solution(instance_for(), solution_for(routes=(route,)))

    assert report.valid is False
    assert expected in issue_codes(report)
    assert "feasibility_claim_mismatch" in issue_codes(report)


@pytest.mark.parametrize(
    "visit, expected",
    [
        (PublicVrptwVisit(1, float("nan"), 5, 10), "timing_invalid"),
        (PublicVrptwVisit(1, 5, 4, 9), "service_start_mismatch"),
        (PublicVrptwVisit(1, 6, 6, 11), "arrival_mismatch"),
        (PublicVrptwVisit(1, 5, 5, 11), "departure_mismatch"),
        (PublicVrptwVisit(1, 5, 51, 56), "time_window_violation"),
    ],
)
def test_verifier_recomputes_every_visit_timing(visit: PublicVrptwVisit, expected: str) -> None:
    route = valid_route(visits=(valid_route().visits[0], visit, *valid_route().visits[2:]))

    report = verify_public_vrptw_solution(instance_for(), solution_for(routes=(route,)))

    assert expected in issue_codes(report)


def test_verifier_detects_capacity_duplicate_vehicle_and_vehicle_limit() -> None:
    overloaded = instance_for(vehicle_capacity=8)
    report = verify_public_vrptw_solution(overloaded, solution_for())
    assert "capacity_violation" in issue_codes(report)

    first = valid_route()
    second = replace(
        valid_route(),
        visits=(PublicVrptwVisit(0, 0, 0, 0), PublicVrptwVisit(0, 0, 0, 0)),
        claimed_distance=0,
    )
    duplicate_vehicle = solution_for(
        routes=(first, second), claimed_vehicle_count=2, claimed_total_distance=20
    )
    report = verify_public_vrptw_solution(instance_for(), duplicate_vehicle)
    assert "vehicle_duplicate" in issue_codes(report)

    report = verify_public_vrptw_solution(instance_for(max_vehicles=1), duplicate_vehicle)
    assert "vehicle_limit_exceeded" in issue_codes(report)


def test_verifier_detects_duplicate_customer_and_unassigned_policy() -> None:
    visits = valid_route().visits
    duplicate_route = valid_route(visits=(visits[0], visits[1], visits[1], visits[2], visits[3]))
    report = verify_public_vrptw_solution(instance_for(), solution_for(routes=(duplicate_route,)))
    assert "customer_duplicate" in issue_codes(report)

    unassigned = solution_for(
        routes=(
            valid_route(
                visits=(
                    PublicVrptwVisit(0, 0, 0, 0),
                    PublicVrptwVisit(1, 5, 5, 10),
                    PublicVrptwVisit(0, 15, 15, 15),
                ),
                claimed_distance=10,
            ),
        ),
        unassigned_node_ids=(2,),
        claimed_total_distance=10,
        claimed_feasible=True,
    )
    strict = verify_public_vrptw_solution(instance_for(), unassigned)
    assert "unassigned_not_allowed" in issue_codes(strict)

    permissive = verify_public_vrptw_solution(instance_for(), unassigned, require_complete=False)
    assert permissive.valid is True
    assert permissive.complete is False


@pytest.mark.parametrize(
    "unassigned, expected",
    [
        ((2, 2), "unassigned_duplicate"),
        ((0,), "unassigned_unknown"),
        ((99,), "unassigned_unknown"),
        ((), "customer_coverage_incomplete"),
    ],
)
def test_verifier_rejects_invalid_unassigned_and_coverage(
    unassigned: tuple[int, ...], expected: str
) -> None:
    route = valid_route(
        visits=(
            PublicVrptwVisit(0, 0, 0, 0),
            PublicVrptwVisit(1, 5, 5, 10),
            PublicVrptwVisit(0, 15, 15, 15),
        ),
        claimed_distance=10,
    )
    report = verify_public_vrptw_solution(
        instance_for(),
        solution_for(
            routes=(route,),
            unassigned_node_ids=unassigned,
            claimed_total_distance=10,
        ),
        require_complete=False,
    )

    assert expected in issue_codes(report)


def test_verifier_detects_assignment_overlap_and_rejects_bad_tolerance() -> None:
    report = verify_public_vrptw_solution(
        instance_for(),
        solution_for(unassigned_node_ids=(2,)),
        require_complete=False,
    )
    assert "assignment_overlap" in issue_codes(report)

    for tolerance in (0, -1, float("nan")):
        with pytest.raises(ValueError, match="tolerance"):
            verify_public_vrptw_solution(instance_for(), solution_for(), tolerance=tolerance)
