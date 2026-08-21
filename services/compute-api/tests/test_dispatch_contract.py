from __future__ import annotations

import pytest

from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchDecision,
    DispatchProblem,
    DispatchStrategy,
    GeoPoint,
)


class FirstCandidateStrategy:
    @property
    def name(self) -> str:
        return "first-candidate-test"

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        courier_id = problem.candidates[0].courier_id if problem.candidates else None
        score = 0.0 if courier_id else None
        return DispatchDecision(problem.request_id, self.name, courier_id, score)


def test_strategy_protocol_accepts_a_stateless_implementation() -> None:
    strategy = FirstCandidateStrategy()
    problem = DispatchProblem(
        request_id="request-1",
        pickup=GeoPoint(31.2304, 121.4737),
        candidates=(CourierCandidate("courier-1", GeoPoint(31.22, 121.48)),),
    )

    assert isinstance(strategy, DispatchStrategy)
    assert strategy.solve(problem).courier_id == "courier-1"


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(90.1, 0.0), (-90.1, 0.0), (0.0, 180.1), (0.0, -180.1)],
)
def test_geo_point_rejects_out_of_range_coordinates(latitude: float, longitude: float) -> None:
    with pytest.raises(ValueError):
        GeoPoint(latitude, longitude)


def test_dispatch_problem_rejects_duplicate_candidates() -> None:
    point = GeoPoint(31.2304, 121.4737)

    with pytest.raises(ValueError, match="unique"):
        DispatchProblem(
            request_id="request-1",
            pickup=point,
            candidates=(CourierCandidate("courier-1", point), CourierCandidate("courier-1", point)),
        )


def test_courier_candidate_rejects_a_blank_identifier() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        CourierCandidate(" ", GeoPoint(31.2304, 121.4737))


def test_dispatch_problem_rejects_a_blank_request_identifier() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        DispatchProblem(" ", GeoPoint(31.2304, 121.4737), ())


def test_dispatch_decision_rejects_blank_identifiers() -> None:
    with pytest.raises(ValueError, match="request_id"):
        DispatchDecision(" ", "test", None, None)

    with pytest.raises(ValueError, match="strategy"):
        DispatchDecision("request-1", " ", None, None)


def test_unassigned_decision_rejects_a_score() -> None:
    with pytest.raises(ValueError, match="cannot have a score"):
        DispatchDecision("request-1", "test", None, 1.0)


def test_dispatch_decision_rejects_invalid_latency_and_version() -> None:
    with pytest.raises(ValueError, match="latency"):
        DispatchDecision("request-1", "test", None, None, latency_millis=-1.0)

    with pytest.raises(ValueError, match="version"):
        DispatchDecision("request-1", "test", None, None, strategy_version=" ")
