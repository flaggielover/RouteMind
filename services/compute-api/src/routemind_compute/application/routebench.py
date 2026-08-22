from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter
from typing import Literal

from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.simulation import (
    ScenarioKernel,
    ScenarioManifest,
    ScenarioRun,
)
from routemind_compute.application.travel import TravelTimeProvider

Metadata = tuple[tuple[str, str], ...]
LineageKind = Literal["hypothesis", "observation", "result", "conclusion"]


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(payload: object) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _normalize_metadata(values: Metadata) -> Metadata:
    normalized = tuple(sorted(values))
    if any(not key.strip() or not value.strip() for key, value in normalized):
        raise ValueError("metadata keys and values must not be blank")
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("metadata keys must be unique")
    return normalized


@dataclass(frozen=True, slots=True)
class BenchmarkManifest:
    manifest_id: str
    code_version: str
    scenario_id: str
    seed: int
    load_profile: str
    city_state: str
    dataset_provenance: str
    strategies: tuple[str, ...]
    configuration: Metadata = ()
    parameter_configuration: Metadata = ()
    runtime: Metadata = ()
    failures: tuple[str, ...] = ()
    hardware: Metadata = ()

    def __post_init__(self) -> None:
        for value, name in (
            (self.manifest_id, "manifest_id"),
            (self.code_version, "code_version"),
            (self.scenario_id, "scenario_id"),
            (self.load_profile, "load_profile"),
            (self.city_state, "city_state"),
            (self.dataset_provenance, "dataset_provenance"),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
        if not self.strategies:
            raise ValueError("at least one strategy is required")
        if any(not strategy.strip() for strategy in self.strategies):
            raise ValueError("strategy names must not be blank")
        if len(set(self.strategies)) != len(self.strategies):
            raise ValueError("strategy names must be unique")
        if any(not failure.strip() for failure in self.failures):
            raise ValueError("failure labels must not be blank")
        object.__setattr__(self, "strategies", tuple(sorted(self.strategies)))
        object.__setattr__(self, "failures", tuple(sorted(set(self.failures))))
        for field_name in ("configuration", "parameter_configuration", "runtime", "hardware"):
            object.__setattr__(self, field_name, _normalize_metadata(getattr(self, field_name)))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "code_version": self.code_version,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "load_profile": self.load_profile,
            "city_state": self.city_state,
            "dataset_provenance": self.dataset_provenance,
            "strategies": self.strategies,
            "configuration": self.configuration,
            "parameter_configuration": self.parameter_configuration,
            "runtime": self.runtime,
            "failures": self.failures,
            "hardware": self.hardware,
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class StrategyBenchmark:
    strategy: str
    strategy_version: str
    request_count: int
    assigned_count: int
    assignment_rate: float
    runtime_millis: float
    replay_digest: str
    run: ScenarioRun

    def __post_init__(self) -> None:
        if self.request_count <= 0 or not 0 <= self.assigned_count <= self.request_count:
            raise ValueError("benchmark counts are invalid")
        if self.runtime_millis < 0:
            raise ValueError("runtime_millis must be non-negative")
        if not self.strategy.strip() or not self.strategy_version.strip():
            raise ValueError("strategy identity must not be blank")

    def deterministic_payload(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "strategy_version": self.strategy_version,
            "request_count": self.request_count,
            "assigned_count": self.assigned_count,
            "assignment_rate": self.assignment_rate,
            "replay_digest": self.replay_digest,
            "decisions": [
                {
                    "request_id": item.request_id,
                    "tick": item.tick,
                    "courier_id": item.courier_id,
                    "strategy": item.strategy,
                    "strategy_version": item.strategy_version,
                }
                for item in self.run.decisions
            ],
            "transitions": [
                {
                    "request_id": item.request_id,
                    "tick": item.tick,
                    "from_state": item.from_state,
                    "to_state": item.to_state,
                    "courier_id": item.courier_id,
                }
                for item in self.run.transitions
            ],
        }


@dataclass(frozen=True, slots=True)
class RouteBenchRun:
    manifest: BenchmarkManifest
    results: tuple[StrategyBenchmark, ...]
    output_digest: str

    def __post_init__(self) -> None:
        if not self.results:
            raise ValueError("RouteBench run must contain results")

    def metrics(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "strategy": result.strategy,
                "strategy_version": result.strategy_version,
                "request_count": result.request_count,
                "assigned_count": result.assigned_count,
                "assignment_rate": result.assignment_rate,
                "runtime_millis": result.runtime_millis,
                "replay_digest": result.replay_digest,
            }
            for result in self.results
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "manifest": self.manifest.canonical_payload(),
            "results": [
                {
                    **result.deterministic_payload(),
                    "runtime_millis": result.runtime_millis,
                }
                for result in self.results
            ],
            "output_digest": self.output_digest,
        }


class RouteBenchRunner:
    def __init__(
        self,
        registry: StrategyRegistry,
        travel_provider: TravelTimeProvider,
        *,
        ticks_per_hour: int = 60,
    ) -> None:
        if ticks_per_hour <= 0:
            raise ValueError("ticks_per_hour must be positive")
        self.registry = registry
        self.travel_provider = travel_provider
        self.ticks_per_hour = ticks_per_hour

    def run(self, manifest: BenchmarkManifest, scenario: ScenarioManifest) -> RouteBenchRun:
        if scenario.scenario_id != manifest.scenario_id or scenario.seed != manifest.seed:
            raise ValueError("benchmark manifest does not match scenario identity")
        results: list[StrategyBenchmark] = []
        for strategy in manifest.strategies:
            started = perf_counter()
            scenario_run = ScenarioKernel(
                self.registry,
                self.travel_provider,
                strategy=strategy,
                ticks_per_hour=self.ticks_per_hour,
                strategy_configuration=manifest.parameter_configuration,
            ).run(scenario)
            runtime_millis = (perf_counter() - started) * 1000
            assigned_count = sum(item.courier_id is not None for item in scenario_run.decisions)
            request_count = len(scenario_run.decisions)
            results.append(
                StrategyBenchmark(
                    strategy,
                    str(getattr(self.registry.get(strategy), "version", "1.0.0")),
                    request_count,
                    assigned_count,
                    assigned_count / request_count,
                    runtime_millis,
                    scenario_run.replay_digest,
                    scenario_run,
                )
            )
        deterministic = {
            "manifest": manifest.digest,
            "results": [result.deterministic_payload() for result in results],
        }
        return RouteBenchRun(manifest, tuple(results), _digest(deterministic))


@dataclass(frozen=True, slots=True)
class LineageNode:
    node_id: str
    kind: LineageKind
    label: str
    manifest_id: str | None
    parents: tuple[str, ...]
    payload: Metadata


class ResearchLineage:
    def __init__(self) -> None:
        self._nodes: dict[str, LineageNode] = {}

    def _record(
        self,
        kind: LineageKind,
        label: str,
        manifest_id: str | None,
        parents: tuple[str, ...],
        payload: Metadata,
    ) -> LineageNode:
        if not label.strip():
            raise ValueError("lineage label must not be blank")
        if manifest_id is not None and not manifest_id.strip():
            raise ValueError("manifest_id must not be blank")
        if len(set(parents)) != len(parents):
            raise ValueError("lineage parents must be unique")
        if any(parent not in self._nodes for parent in parents):
            raise KeyError("lineage parent does not exist")
        normalized = _normalize_metadata(payload)
        node_id = _digest(
            {
                "kind": kind,
                "label": label,
                "manifest_id": manifest_id,
                "parents": parents,
                "payload": normalized,
            }
        )
        node = LineageNode(node_id, kind, label, manifest_id, parents, normalized)
        existing = self._nodes.get(node_id)
        if existing is not None and existing != node:
            raise ValueError("lineage node identifier collision")
        self._nodes[node_id] = node
        return node

    def record_hypothesis(self, statement: str, *, label: str = "hypothesis") -> LineageNode:
        return self._record("hypothesis", label, None, (), (("statement", statement),))

    def record_observation(
        self, hypothesis_id: str, manifest_id: str, key: str, value: str
    ) -> LineageNode:
        return self._record(
            "observation", "observation", manifest_id, (hypothesis_id,), ((key, value),)
        )

    def record_result(
        self, manifest_id: str, run: RouteBenchRun, *, parents: tuple[str, ...] = ()
    ) -> LineageNode:
        if run.manifest.manifest_id != manifest_id:
            raise ValueError("result manifest does not match lineage manifest")
        return self._record(
            "result",
            "routebench-result",
            manifest_id,
            parents,
            (("output_digest", run.output_digest), ("manifest_digest", run.manifest.digest)),
        )

    def record_conclusion(self, hypothesis_id: str, result_id: str, statement: str) -> LineageNode:
        return self._record(
            "conclusion",
            "conclusion",
            self._nodes[result_id].manifest_id if result_id in self._nodes else None,
            (hypothesis_id, result_id),
            (("statement", statement),),
        )

    def query(
        self,
        *,
        manifest_id: str | None = None,
        hypothesis_id: str | None = None,
        kind: LineageKind | None = None,
    ) -> tuple[LineageNode, ...]:
        if hypothesis_id is not None and hypothesis_id not in self._nodes:
            raise KeyError("hypothesis does not exist")
        selected = tuple(self._nodes.values())
        if manifest_id is not None:
            selected = tuple(node for node in selected if node.manifest_id == manifest_id)
        if kind is not None:
            selected = tuple(node for node in selected if node.kind == kind)
        if hypothesis_id is not None:
            selected = tuple(
                node
                for node in selected
                if node.node_id == hypothesis_id or self._descends_from(node, hypothesis_id)
            )
        return tuple(sorted(selected, key=lambda node: node.node_id))

    def _descends_from(self, node: LineageNode, ancestor_id: str) -> bool:
        pending = list(node.parents)
        visited: set[str] = set()
        while pending:
            parent_id = pending.pop()
            if parent_id == ancestor_id:
                return True
            if parent_id not in visited:
                visited.add(parent_id)
                pending.extend(self._nodes[parent_id].parents)
        return False

    @property
    def nodes(self) -> tuple[LineageNode, ...]:
        return tuple(sorted(self._nodes.values(), key=lambda node: node.node_id))

    def payload(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "node_id": node.node_id,
                "kind": node.kind,
                "label": node.label,
                "manifest_id": node.manifest_id,
                "parents": node.parents,
                "payload": node.payload,
            }
            for node in self.nodes
        )
