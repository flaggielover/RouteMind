from __future__ import annotations

import pytest

from routemind_compute.application.baselines import HungarianStrategy, WeightedGreedyStrategy
from routemind_compute.application.benchmark import benchmark_problem
from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint


def make_problem() -> DispatchProblem:
    return DispatchProblem(
        "request-1",
        GeoPoint(31.2304, 121.4737),
        (CourierCandidate("courier-b", GeoPoint(31.22, 121.48)),),
    )


def test_baselines_conform_to_registry_and_are_versioned() -> None:
    registry = default_registry()
    assert registry.names() == ("hungarian", "nearest", "risk-aware", "weighted-greedy")
    results = [registry.solve(name, make_problem()) for name in registry.names()]
    assert {result.strategy_version for result in results} == {"1.0.0"}
    assert {result.courier_id for result in results} == {"courier-b"}


def test_hungarian_assignment_solves_rectangular_and_transposed_matrices() -> None:
    strategy = HungarianStrategy()
    assert strategy.assign(((4.0, 1.0), (2.0, 3.0))) == ((0, 1), (1, 0))
    assert strategy.assign(((4.0,), (2.0,))) == ((1, 0),)

    with pytest.raises(ValueError, match="rectangular"):
        strategy.assign(((1.0,), (1.0, 2.0)))
    with pytest.raises(ValueError, match="finite"):
        strategy.assign(((float("inf"),),))


def test_weighted_greedy_rejects_invalid_weights_and_benchmark_records_provenance() -> None:
    with pytest.raises(ValueError, match="positive"):
        WeightedGreedyStrategy(0).solve(make_problem())
    with pytest.raises(ValueError, match="positive"):
        WeightedGreedyStrategy(float("inf")).solve(make_problem())

    empty = DispatchProblem("empty", GeoPoint(0, 0), ())
    assert WeightedGreedyStrategy().solve(empty).courier_id is None
    assert HungarianStrategy().solve(empty).courier_id is None

    records = benchmark_problem(
        StrategyRegistry((NearestStrategy(), WeightedGreedyStrategy())),
        make_problem(),
        provenance="rm031-smoke-v1",
    )
    assert {record.strategy for record in records} == {"nearest", "weighted-greedy"}
    assert all(record.provenance == "rm031-smoke-v1" for record in records)
    assert all(record.latency_millis >= 0 for record in records)
