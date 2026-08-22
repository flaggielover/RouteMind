from __future__ import annotations

import pytest

from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.routebench import (
    BenchmarkManifest,
    ResearchLineage,
    RouteBenchRun,
    RouteBenchRunner,
    StrategyBenchmark,
)
from routemind_compute.application.simulation import (
    CourierState,
    DemandEvent,
    ScenarioManifest,
)
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.domain.dispatch import GeoPoint


def scenario() -> ScenarioManifest:
    return ScenarioManifest(
        "scenario-routebench",
        11,
        (
            DemandEvent("request-1", GeoPoint(31.2304, 121.4737), 0),
            DemandEvent("request-2", GeoPoint(31.2305, 121.4738), 0),
        ),
        (
            CourierState("courier-1", GeoPoint(31.22, 121.48)),
            CourierState("courier-2", GeoPoint(31.24, 121.46)),
        ),
        delay_ticks=(0,),
    )


def manifest() -> BenchmarkManifest:
    return BenchmarkManifest(
        "manifest-1",
        "git:c1913f3",
        "scenario-routebench",
        11,
        "reduced-2x2",
        "shanghai-local",
        "fixture:routebench-v1",
        ("weighted-greedy", "nearest"),
        configuration=(("batch_size", "2"), ("traffic", "1.0")),
        runtime=(("python", "3.14"),),
        failures=("none",),
        hardware=(("platform", "local"),),
    )


def runner() -> RouteBenchRunner:
    from routemind_compute.application.baselines import WeightedGreedyStrategy

    return RouteBenchRunner(
        StrategyRegistry((NearestStrategy(), WeightedGreedyStrategy())),
        DeterministicLocalTravelProvider(),
    )


def test_manifest_canonicalizes_metadata_and_records_research_provenance() -> None:
    value = manifest()

    assert value.strategies == ("nearest", "weighted-greedy")
    assert value.configuration == (("batch_size", "2"), ("traffic", "1.0"))
    assert len(value.digest) == 64
    assert value.canonical_payload()["dataset_provenance"] == "fixture:routebench-v1"

    with pytest.raises(ValueError, match="at least one strategy"):
        BenchmarkManifest("m", "c", "s", 1, "load", "city", "data", ())
    with pytest.raises(ValueError, match="unique"):
        BenchmarkManifest("m", "c", "s", 1, "load", "city", "data", ("a", "a"))
    with pytest.raises(ValueError, match="strategy names"):
        BenchmarkManifest("m", "c", "s", 1, "load", "city", "data", (" ",))
    with pytest.raises(ValueError, match="failure labels"):
        BenchmarkManifest("m", "c", "s", 1, "load", "city", "data", ("a",), failures=(" ",))
    with pytest.raises(ValueError, match="metadata keys"):
        BenchmarkManifest(
            "m", "c", "s", 1, "load", "city", "data", ("a",), configuration=(("x", "1"), ("x", "2"))
        )
    with pytest.raises(ValueError, match="metadata keys and values"):
        BenchmarkManifest(
            "m", "c", "s", 1, "load", "city", "data", ("a",), configuration=(("", "1"),)
        )


def test_routebench_compares_registered_strategies_with_stable_output_digest() -> None:
    first = runner().run(manifest(), scenario())
    second = runner().run(manifest(), scenario())

    assert first.output_digest == second.output_digest
    assert [result.strategy for result in first.results] == ["nearest", "weighted-greedy"]
    assert all(result.request_count == 2 for result in first.results)
    assert all(result.assigned_count == 2 for result in first.results)
    assert all(metric["assignment_rate"] == 1.0 for metric in first.metrics())
    assert all(result.runtime_millis >= 0 for result in first.results)
    assert first.canonical_payload()["output_digest"] == first.output_digest

    with pytest.raises(ValueError, match="does not match"):
        runner().run(
            manifest(), ScenarioManifest("other", 11, scenario().demands, scenario().couriers)
        )
    with pytest.raises(ValueError, match="ticks_per_hour"):
        RouteBenchRunner(
            StrategyRegistry((NearestStrategy(),)),
            DeterministicLocalTravelProvider(),
            ticks_per_hour=0,
        )


def test_lineage_is_typed_parented_and_queryable() -> None:
    run = runner().run(manifest(), scenario())
    lineage = ResearchLineage()
    hypothesis = lineage.record_hypothesis("Nearest and weighted greedy assign all reduced demands")
    observation = lineage.record_observation(
        hypothesis.node_id, manifest().manifest_id, "assigned", "2/2"
    )
    result = lineage.record_result(manifest().manifest_id, run, parents=(observation.node_id,))
    conclusion = lineage.record_conclusion(
        hypothesis.node_id, result.node_id, "Supported in the reduced fixture"
    )

    nodes = lineage.query(hypothesis_id=hypothesis.node_id)
    assert {node.kind for node in nodes} == {"hypothesis", "observation", "result", "conclusion"}
    assert {node.kind for node in lineage.query(manifest_id=manifest().manifest_id)} == {
        "observation",
        "result",
        "conclusion",
    }
    assert lineage.query(kind="conclusion") == (conclusion,)
    assert all(len(node.node_id) == 64 for node in lineage.nodes)
    assert lineage.payload()[-1]["node_id"] in {node.node_id for node in lineage.nodes}

    with pytest.raises(KeyError, match="parent"):
        lineage.record_observation("missing", "manifest-1", "key", "value")
    with pytest.raises(ValueError, match="label"):
        lineage.record_hypothesis("statement", label=" ")
    with pytest.raises(ValueError, match="manifest_id"):
        lineage.record_observation(hypothesis.node_id, " ", "key", "value")
    with pytest.raises(ValueError, match="parents"):
        lineage.record_result(
            manifest().manifest_id,
            run,
            parents=(observation.node_id, observation.node_id),
        )
    assert (
        lineage.record_result(manifest().manifest_id, run, parents=(observation.node_id,)) == result
    )
    with pytest.raises(KeyError, match="hypothesis"):
        lineage.query(hypothesis_id="missing")
    with pytest.raises(ValueError, match="does not match"):
        lineage.record_result("other", run)
    with pytest.raises(KeyError, match="parent"):
        lineage.record_conclusion(hypothesis.node_id, "missing", "unknown")


def test_benchmark_result_validation_rejects_invalid_counts() -> None:
    run = runner().run(manifest(), scenario()).results[0].run

    with pytest.raises(ValueError, match="counts"):
        StrategyBenchmark("nearest", "1.0.0", 0, 0, 0.0, 0.0, run.replay_digest, run)
    with pytest.raises(ValueError, match="runtime"):
        StrategyBenchmark("nearest", "1.0.0", 1, 1, 1.0, -1.0, run.replay_digest, run)
    with pytest.raises(ValueError, match="identity"):
        StrategyBenchmark(" ", "1.0.0", 1, 1, 1.0, 0.0, run.replay_digest, run)
    with pytest.raises(ValueError, match="results"):
        RouteBenchRun(manifest(), (), "digest")
