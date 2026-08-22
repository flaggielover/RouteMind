from dataclasses import dataclass, replace
from time import perf_counter

from routemind_compute.application.parameters import Metadata, StrategyParameterSchema, schema_for
from routemind_compute.domain.dispatch import DispatchDecision, DispatchProblem, DispatchStrategy


@dataclass(frozen=True, slots=True)
class StrategyDescriptor:
    name: str
    version: str
    capabilities: tuple[str, ...]
    status: str = "available"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("strategy name must not be blank")
        if not self.version.strip():
            raise ValueError("strategy version must not be blank")
        if not self.capabilities or any(not capability.strip() for capability in self.capabilities):
            raise ValueError("strategy capabilities must not be blank")
        if self.status != "available":
            raise ValueError("registered strategy status must be available")


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

    def descriptors(self) -> tuple[StrategyDescriptor, ...]:
        descriptors = []
        for name in self.names():
            strategy = self._strategies[name]
            version = str(getattr(strategy, "version", "")).strip()
            capabilities = tuple(
                sorted(
                    {
                        str(capability).strip()
                        for capability in getattr(strategy, "capabilities", ("dispatch",))
                    }
                )
            )
            descriptors.append(StrategyDescriptor(name, version, capabilities))
        return tuple(descriptors)

    def parameter_schemas(self) -> tuple[StrategyParameterSchema, ...]:
        return tuple(
            schema_for(descriptor.name, descriptor.version) for descriptor in self.descriptors()
        )

    def parameter_schema(self, name: str) -> StrategyParameterSchema:
        strategy = self.get(name)
        return schema_for(name, str(getattr(strategy, "version", "1.0.0")))

    def get(self, name: str) -> DispatchStrategy:
        try:
            return self._strategies[name]
        except KeyError as error:
            raise KeyError(f"unknown dispatch strategy: {name}") from error

    def solve(
        self, name: str, problem: DispatchProblem, configuration: Metadata = ()
    ) -> DispatchDecision:
        strategy = self._configured(name, configuration)
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

    def _configured(self, name: str, configuration: Metadata) -> DispatchStrategy:
        base = self.get(name)
        if not configuration:
            return base
        normalized = self.parameter_schema(name).validate(configuration)
        values = dict(normalized)
        if name == "weighted-greedy":
            from routemind_compute.application.baselines import WeightedGreedyStrategy

            return WeightedGreedyStrategy(float(values["distance_weight"]))
        if name == "risk-aware":
            from routemind_compute.application.risk_aware import (
                RiskAwareScoringStrategy,
                RiskAwareWeights,
            )

            return RiskAwareScoringStrategy(
                RiskAwareWeights(
                    float(values["distance"]),
                    float(values["readiness"]),
                    float(values["overtime"]),
                    float(values["service_risk"]),
                    float(values["balance"]),
                )
            )
        raise ValueError(f"strategy does not expose configurable parameters: {name}")


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
