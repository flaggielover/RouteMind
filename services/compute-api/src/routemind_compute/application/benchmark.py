from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.domain.dispatch import DispatchProblem


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    request_id: str
    strategy: str
    strategy_version: str
    latency_millis: float
    courier_id: str | None
    provenance: str


def benchmark_problem(
    registry: StrategyRegistry, problem: DispatchProblem, *, provenance: str
) -> tuple[BenchmarkRecord, ...]:
    records: list[BenchmarkRecord] = []
    for strategy in registry.names():
        started = perf_counter()
        decision = registry.solve(strategy, problem)
        elapsed = (perf_counter() - started) * 1000
        records.append(
            BenchmarkRecord(
                problem.request_id,
                decision.strategy,
                decision.strategy_version,
                elapsed,
                decision.courier_id,
                provenance,
            )
        )
    return tuple(records)
