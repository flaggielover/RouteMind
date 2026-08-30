from dataclasses import dataclass, replace
from time import perf_counter
from typing import Literal

from opentelemetry.trace import Tracer, get_tracer

from routemind_compute.application.parameters import Metadata, StrategyParameterSchema, schema_for
from routemind_compute.application.verification import (
    SolverOutputInvalidError,
    verify_dispatch_decision,
)
from routemind_compute.domain.dispatch import DispatchDecision, DispatchProblem, DispatchStrategy

StrategyMaturity = Literal[
    "BASELINE", "ENGINEERING", "PRODUCTION-CANDIDATE", "RESEARCH", "EXTERNAL-VALIDATED"
]
_MATURITY_BY_STRATEGY: dict[str, StrategyMaturity] = {
    "nearest": "BASELINE",
    "weighted-greedy": "BASELINE",
    "hungarian": "BASELINE",
    "minimum-cost-flow": "ENGINEERING",
    "partitioned-assignment": "ENGINEERING",
    "local-search": "ENGINEERING",
    # This is a bounded deterministic insertion heuristic for small instances.
    "vrptw": "BASELINE",
}


@dataclass(frozen=True, slots=True)
class StrategyDescriptor:
    name: str
    version: str
    capabilities: tuple[str, ...]
    status: str = "available"
    maturity: StrategyMaturity = "BASELINE"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("strategy name must not be blank")
        if not self.version.strip():
            raise ValueError("strategy version must not be blank")
        if not self.capabilities or any(not capability.strip() for capability in self.capabilities):
            raise ValueError("strategy capabilities must not be blank")
        if self.status != "available":
            raise ValueError("registered strategy status must be available")
        if self.maturity not in {
            "BASELINE",
            "ENGINEERING",
            "PRODUCTION-CANDIDATE",
            "RESEARCH",
            "EXTERNAL-VALIDATED",
        }:
            raise ValueError("strategy maturity label is not supported")


class StrategyRegistry:
    """Versioned strategy lookup and result instrumentation boundary."""

    def __init__(
        self, strategies: tuple[DispatchStrategy, ...] = (), *, tracer: Tracer | None = None
    ) -> None:
        self._strategies: dict[str, DispatchStrategy] = {}
        self._tracer = tracer or get_tracer("routemind.compute.solver", "v1")
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
            maturity = getattr(strategy, "maturity", _MATURITY_BY_STRATEGY.get(name, "BASELINE"))
            descriptors.append(StrategyDescriptor(name, version, capabilities, maturity=maturity))
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
        with self._tracer.start_as_current_span(
            "routemind.solver.solve",
            attributes={
                "routemind.request_id": problem.request_id,
                "routemind.strategy": strategy.name,
                "routemind.candidate_count": len(problem.candidates),
            },
        ) as solver_span:
            started = perf_counter()
            decision = strategy.solve(problem)
            elapsed_millis = (perf_counter() - started) * 1000
            solver_span.set_attribute("routemind.solver.duration_ms", elapsed_millis)
            solver_span.set_attribute(
                "routemind.decision.assigned", decision.courier_id is not None
            )
            if decision.request_id != problem.request_id:
                raise ValueError("strategy returned a decision for a different request")
            if decision.strategy != strategy.name:
                raise ValueError("strategy returned a decision with a different strategy name")
            version = str(getattr(strategy, "version", decision.strategy_version)).strip()
            if not version:
                raise ValueError("strategy version must not be blank")
            with self._tracer.start_as_current_span(
                "routemind.decision.verify",
                attributes={
                    "routemind.decision_id": decision.request_id,
                    "routemind.strategy": strategy.name,
                },
            ) as verification_span:
                report = verify_dispatch_decision(problem, decision, strategy)
                verification_span.set_attribute("routemind.decision.valid", report.valid)
                if not report.valid:
                    raise SolverOutputInvalidError(report)
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
        if name == "local-search":
            from routemind_compute.application.local_search import (
                LocalSearchConfig,
                LocalSearchStrategy,
            )

            return LocalSearchStrategy(
                LocalSearchConfig(max_iterations=int(values["max_iterations"]))
            )
        raise ValueError(f"strategy does not expose configurable parameters: {name}")


def default_registry(*, tracer: Tracer | None = None) -> StrategyRegistry:
    from routemind_compute.application.baselines import HungarianStrategy, WeightedGreedyStrategy
    from routemind_compute.application.flow import (
        MinimumCostFlowStrategy,
        PartitionedAssignmentStrategy,
    )
    from routemind_compute.application.local_search import LocalSearchStrategy
    from routemind_compute.application.nearest import NearestStrategy
    from routemind_compute.application.risk_aware import RiskAwareScoringStrategy
    from routemind_compute.application.vrptw import VrptwStrategy

    return StrategyRegistry(
        (
            NearestStrategy(),
            WeightedGreedyStrategy(),
            HungarianStrategy(),
            RiskAwareScoringStrategy(),
            MinimumCostFlowStrategy(),
            PartitionedAssignmentStrategy(),
            VrptwStrategy(),
            LocalSearchStrategy(),
        ),
        tracer=tracer,
    )
