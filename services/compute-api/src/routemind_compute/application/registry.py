from __future__ import annotations

from dataclasses import replace
from time import perf_counter

from routemind_compute.domain.dispatch import DispatchDecision, DispatchProblem, DispatchStrategy


class StrategyRegistry:
    """Versioned strategy lookup and result instrumentation boundary."""

    def __init__(self, strategies: tuple[DispatchStrategy, ...] = ()) -> None:
        self._strategies: dict[str, DispatchStrategy] = {}
        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy: DispatchStrategy) -> None:
        name = strategy.name.strip()
        if not name:
            raise ValueError("strategy name must not be blank")
        if name in self._strategies:
            raise ValueError(f"strategy already registered: {name}")
        self._strategies[name] = strategy

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._strategies))

    def get(self, name: str) -> DispatchStrategy:
        try:
            return self._strategies[name]
        except KeyError as error:
            raise KeyError(f"unknown dispatch strategy: {name}") from error

    def solve(self, name: str, problem: DispatchProblem) -> DispatchDecision:
        strategy = self.get(name)
        started = perf_counter()
        decision = strategy.solve(problem)
        elapsed_millis = (perf_counter() - started) * 1000
        if decision.request_id != problem.request_id:
            raise ValueError("strategy returned a decision for a different request")
        if decision.strategy != strategy.name:
            raise ValueError("strategy returned a decision with a different strategy name")
        version = str(getattr(strategy, "version", decision.strategy_version)).strip()
        if not version:
            raise ValueError("strategy version must not be blank")
        metadata = (
            *decision.metadata,
            ("candidate_count", str(len(problem.candidates))),
            ("eligible_candidate_count", str(len(problem.eligible_candidates()))),
            ("assigned", str(decision.courier_id is not None).lower()),
        )
        if decision.courier_id is None:
            metadata = (
                *metadata,
                ("infeasibility_reasons", "|".join(problem.infeasibility_reasons())),
            )
        return replace(
            decision,
            strategy_version=version,
            latency_millis=elapsed_millis,
            metadata=metadata,
        )


def default_registry() -> StrategyRegistry:
    from routemind_compute.application.baselines import HungarianStrategy, WeightedGreedyStrategy
    from routemind_compute.application.flow import (
        MinimumCostFlowStrategy,
        PartitionedAssignmentStrategy,
    )
    from routemind_compute.application.nearest import NearestStrategy
    from routemind_compute.application.risk_aware import RiskAwareScoringStrategy

    return StrategyRegistry(
        (
            NearestStrategy(),
            WeightedGreedyStrategy(),
            HungarianStrategy(),
            RiskAwareScoringStrategy(),
            MinimumCostFlowStrategy(),
            PartitionedAssignmentStrategy(),
        )
    )
