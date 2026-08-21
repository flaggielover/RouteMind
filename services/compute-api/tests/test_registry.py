from __future__ import annotations

import pytest

from routemind_compute.application.nearest import NearestStrategy, great_circle_distance_kilometres
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchDecision,
    DispatchProblem,
    GeoPoint,
)


def problem(*candidates: CourierCandidate) -> DispatchProblem:
    return DispatchProblem("request-1", GeoPoint(31.2304, 121.4737), tuple(candidates))


def test_nearest_is_deterministic_under_equal_distance_ties() -> None:
    pickup = GeoPoint(0.0, 0.0)
    result = NearestStrategy().solve(
        DispatchProblem(
            "request-1",
            pickup,
            (
                CourierCandidate("courier-b", GeoPoint(0.0, 1.0)),
                CourierCandidate("courier-a", GeoPoint(0.0, -1.0)),
            ),
        )
    )

    assert result.courier_id == "courier-a"
    assert result.strategy_version == "1.0.0"
    assert result.score == pytest.approx(great_circle_distance_kilometres(0, 0, 0, 1))


def test_nearest_returns_an_unassigned_decision_without_candidates() -> None:
    result = NearestStrategy().solve(problem())

    assert result.courier_id is None
    assert result.score is None
    assert result.rationale == ("no eligible courier",)


def test_registry_records_version_latency_and_decision_metadata() -> None:
    registry = StrategyRegistry((NearestStrategy(),))
    result = registry.solve(
        "nearest",
        problem(CourierCandidate("courier-1", GeoPoint(31.22, 121.48))),
    )

    assert registry.names() == ("nearest",)
    assert result.latency_millis >= 0
    assert dict(result.metadata) == {"candidate_count": "1", "assigned": "true"}


def test_registry_rejects_duplicate_and_unknown_strategies() -> None:
    registry = StrategyRegistry((NearestStrategy(),))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(NearestStrategy())
    with pytest.raises(KeyError, match="unknown"):
        registry.get("missing")

    class BlankNameStrategy:
        name = " "

        def solve(self, dispatch_problem: DispatchProblem) -> DispatchDecision:
            return DispatchDecision(dispatch_problem.request_id, self.name, None, None)

    with pytest.raises(ValueError, match="name"):
        StrategyRegistry((BlankNameStrategy(),))


def test_registry_rejects_mismatched_strategy_results() -> None:
    class BrokenStrategy:
        name = "broken"
        version = "1.0.0"

        def solve(self, dispatch_problem: DispatchProblem) -> DispatchDecision:
            return DispatchDecision(dispatch_problem.request_id, "other", None, None)

    with pytest.raises(ValueError, match="different strategy"):
        StrategyRegistry((BrokenStrategy(),)).solve("broken", problem())


def test_registry_rejects_wrong_request_and_blank_version_results() -> None:
    class WrongRequestStrategy:
        name = "wrong-request"
        version = "1.0.0"

        def solve(self, dispatch_problem: DispatchProblem) -> DispatchDecision:
            return DispatchDecision("other-request", self.name, None, None)

    with pytest.raises(ValueError, match="different request"):
        StrategyRegistry((WrongRequestStrategy(),)).solve("wrong-request", problem())

    class BlankVersionStrategy:
        name = "blank-version"
        version = " "

        def solve(self, dispatch_problem: DispatchProblem) -> DispatchDecision:
            return DispatchDecision(dispatch_problem.request_id, self.name, None, None)

    with pytest.raises(ValueError, match="version"):
        StrategyRegistry((BlankVersionStrategy(),)).solve("blank-version", problem())
