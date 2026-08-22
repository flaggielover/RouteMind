from __future__ import annotations

import pytest

from routemind_compute.application.flow import (
    BatchDispatchProblem,
    BatchDispatchRequest,
    MinimumCostFlowStrategy,
    PartitionedAssignmentStrategy,
)
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint


def batch_problem() -> BatchDispatchProblem:
    return BatchDispatchProblem(
        "batch-1",
        (
            BatchDispatchRequest("request-a", GeoPoint(0, 0), partition="north"),
            BatchDispatchRequest("request-b", GeoPoint(0, 1), partition="north"),
            BatchDispatchRequest("request-c", GeoPoint(1, 0), partition="south"),
        ),
        (
            CourierCandidate("courier-n1", GeoPoint(0, 0), capacity_units=2, zone="north"),
            CourierCandidate("courier-n2", GeoPoint(0, 1), capacity_units=1, zone="north"),
            CourierCandidate("courier-s1", GeoPoint(1, 0), capacity_units=1, zone="south"),
        ),
    )


def test_minimum_cost_flow_handles_rectangular_capacity_and_global_optimum() -> None:
    result = MinimumCostFlowStrategy().assign_batch(batch_problem())

    assert [(item.request_id, item.courier_id) for item in result.assignments] == [
        ("request-a", "courier-n1"),
        ("request-b", "courier-n2"),
        ("request-c", "courier-s1"),
    ]
    assert result.unassigned == ()
    assert result.total_cost >= 0
    assert result.latency_millis >= 0


def test_minimum_cost_flow_uses_residual_rematching_for_global_optimum() -> None:
    from routemind_compute.application.flow import _minimum_cost_flow

    assigned, unassigned, total = _minimum_cost_flow(((1.0, 2.0), (1.1, 100.0)), (1, 1))

    assert assigned == ((0, 1, 2.0), (1, 0, 1.1))
    assert unassigned == ()
    assert total == pytest.approx(3.1)


def test_partitioned_assignment_does_not_cross_zone_boundaries() -> None:
    first = PartitionedAssignmentStrategy().assign_batch(batch_problem())
    second = PartitionedAssignmentStrategy().assign_batch(batch_problem())

    assert first.assignments == second.assignments
    assert first.unassigned == second.unassigned
    assert first.total_cost == second.total_cost
    assert {item.courier_id for item in first.assignments} == {
        "courier-n1",
        "courier-n2",
        "courier-s1",
    }


def test_flow_reports_capacity_infeasibility_and_registry_single_request_metadata() -> None:
    problem = BatchDispatchProblem(
        "batch-2",
        (
            BatchDispatchRequest("request-a", GeoPoint(0, 0)),
            BatchDispatchRequest("request-b", GeoPoint(0, 0)),
        ),
        (CourierCandidate("only", GeoPoint(0, 0), capacity_units=1),),
    )
    result = MinimumCostFlowStrategy().assign_batch(problem)
    assert len(result.assignments) == 1
    assert result.unassigned == (("request-b", "no courier capacity"),)

    decision = MinimumCostFlowStrategy().solve(
        DispatchProblem("single", GeoPoint(0, 0), problem.candidates)
    )
    assert decision.courier_id == "only"
    assert dict(decision.metadata)["assignment_mode"] == "successive-shortest-augmenting-path"


def test_flow_rejects_invalid_batches() -> None:
    with pytest.raises(ValueError, match="unique"):
        BatchDispatchProblem(
            "batch",
            (
                BatchDispatchRequest("same", GeoPoint(0, 0)),
                BatchDispatchRequest("same", GeoPoint(0, 1)),
            ),
            (),
        )
    with pytest.raises(ValueError, match="rectangular"):
        from routemind_compute.application.flow import _minimum_cost_flow

        _minimum_cost_flow(((1.0,), (1.0, 2.0)), (1,))
