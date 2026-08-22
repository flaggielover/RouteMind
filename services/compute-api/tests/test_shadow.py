from __future__ import annotations

from dataclasses import replace
from math import inf
from typing import cast

import pytest

from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.shadow import (
    DecisionSnapshot,
    RegressionAction,
    RegressionAssessment,
    RegressionGate,
    RegressionPolicy,
    ShadowManifest,
    ShadowMetrics,
    ShadowModeEvaluator,
    ShadowObservation,
    ShadowRun,
)
from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchDecision,
    DispatchProblem,
    GeoPoint,
)


class SameAsNearestStrategy:
    name = "candidate-same"
    version = "1.0.0"

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        nearest = NearestStrategy().solve(problem)
        return replace(nearest, strategy=self.name, strategy_version=self.version)


class AlternateStrategy:
    name = "candidate-alternate"
    version = "1.0.0"

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        if not problem.candidates:
            return DispatchDecision(problem.request_id, self.name, None, None)
        courier = sorted(problem.candidates, key=lambda item: item.courier_id)[-1]
        return DispatchDecision(problem.request_id, self.name, courier.courier_id, 2.0)


class FailingStrategy:
    name = "candidate-failing"
    version = "1.0.0"

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        raise RuntimeError(f"must not leak request {problem.request_id}")


def problem(request_id: str = "request-1") -> DispatchProblem:
    return DispatchProblem(
        request_id,
        GeoPoint(31.2304, 121.4737),
        (
            CourierCandidate("courier-a", GeoPoint(31.2305, 121.4738)),
            CourierCandidate("courier-b", GeoPoint(31.2400, 121.4800)),
        ),
    )


def manifest(
    candidate: str = "candidate-same", policy: RegressionPolicy | None = None
) -> ShadowManifest:
    return ShadowManifest(
        "shadow-1",
        "git:c71241c",
        "shadow-fixture",
        23,
        "nearest",
        candidate,
        policy or RegressionPolicy(),
        configuration=(("fixture", "two-couriers"),),
    )


def evaluator(*strategies: object) -> ShadowModeEvaluator:
    return ShadowModeEvaluator(StrategyRegistry((NearestStrategy(), *strategies)))  # type: ignore[arg-type]


def test_shadow_keeps_active_authority_and_canonicalizes_problem_order() -> None:
    shadow = evaluator(SameAsNearestStrategy())
    first = shadow.run(manifest(), (problem("request-2"), problem("request-1")))
    second = shadow.run(manifest(), (problem("request-1"), problem("request-2")))

    assert first.output_digest == second.output_digest
    assert [item.request_id for item in first.observations] == ["request-1", "request-2"]
    assert all(item.authoritative.strategy == "nearest" for item in first.observations)
    assert all(item.authoritative.courier_id == "courier-a" for item in first.observations)
    assert all(item.candidate is not None for item in first.observations)
    assert first.metrics == ShadowMetrics(2, 1.0, 1.0, 0.0, 0.0)
    assert first.canonical_payload()["output_digest"] == first.output_digest
    assert first.observed_payload()["output_digest"] == first.output_digest
    assert "latency_millis" in first.observations[0].authoritative.observed_payload()
    assert "latency_millis" not in first.observations[0].authoritative.deterministic_payload()


def test_candidate_failure_is_bounded_and_active_failure_is_not_hidden() -> None:
    run = evaluator(FailingStrategy()).run(manifest("candidate-failing"), (problem(),))

    observation = run.observations[0]
    assert observation.authoritative.courier_id == "courier-a"
    assert observation.candidate is None
    assert observation.candidate_error == "candidate_execution_failed:RuntimeError"
    assert "request-1" not in observation.candidate_error
    assert observation.disagrees
    assert run.metrics == ShadowMetrics(1, 1.0, 0.0, 1.0, 1.0)

    active_fails = ShadowModeEvaluator(
        StrategyRegistry((FailingStrategy(), SameAsNearestStrategy()))
    )
    active_manifest = replace(
        manifest(), active_strategy="candidate-failing", candidate_strategy="candidate-same"
    )
    with pytest.raises(RuntimeError, match="must not leak"):
        active_fails.run(active_manifest, (problem(),))


def test_regression_gate_promotes_at_boundaries_and_holds_with_stable_reasons() -> None:
    promote_policy = RegressionPolicy(
        minimum_samples=2,
        maximum_failure_rate=0.0,
        maximum_assignment_rate_drop=0.0,
        maximum_disagreement_rate=0.0,
    )
    promote_run = evaluator(SameAsNearestStrategy()).run(
        manifest(policy=promote_policy), (problem("request-1"), problem("request-2"))
    )
    promoted = RegressionGate().assess(promote_run)
    assert promoted.action == "promote"
    assert promoted.reasons == ()
    assert promoted.payload()["run_digest"] == promote_run.output_digest

    hold_policy = RegressionPolicy(
        minimum_samples=2,
        maximum_failure_rate=0.0,
        maximum_assignment_rate_drop=0.0,
        maximum_disagreement_rate=0.0,
    )
    hold_run = evaluator(FailingStrategy()).run(
        manifest("candidate-failing", hold_policy), (problem(),)
    )
    held = RegressionGate().assess(hold_run)
    assert held.action == "hold"
    assert held.reasons == (
        "insufficient_samples",
        "candidate_failure_rate_exceeded",
        "assignment_rate_drop_exceeded",
        "disagreement_rate_exceeded",
    )


def test_alternate_candidate_is_measured_as_disagreement_without_losing_authority() -> None:
    run = evaluator(AlternateStrategy()).run(
        manifest(
            "candidate-alternate",
            RegressionPolicy(maximum_disagreement_rate=1.0),
        ),
        (problem(),),
    )
    observation = run.observations[0]
    assert observation.authoritative.courier_id == "courier-a"
    assert observation.candidate is not None
    assert observation.candidate.courier_id == "courier-b"
    assert run.metrics.disagreement_rate == 1.0
    assert RegressionGate().assess(run).action == "promote"


def test_manifest_policy_and_run_validation_reject_invalid_values() -> None:
    value = manifest()
    assert value.configuration == (("fixture", "two-couriers"),)
    assert len(value.digest) == 64

    with pytest.raises(ValueError, match="minimum_samples"):
        RegressionPolicy(minimum_samples=0)
    with pytest.raises(ValueError, match="between 0 and 1"):
        RegressionPolicy(maximum_failure_rate=inf)
    with pytest.raises(ValueError, match="must differ"):
        replace(value, candidate_strategy="nearest")
    with pytest.raises(ValueError, match="metadata keys"):
        replace(value, configuration=(("x", "1"), ("x", "2")))
    with pytest.raises(ValueError, match="at least one problem"):
        evaluator(SameAsNearestStrategy()).run(value, ())
    with pytest.raises(ValueError, match="unique"):
        evaluator(SameAsNearestStrategy()).run(value, (problem(), problem()))
    with pytest.raises(KeyError, match="unknown"):
        evaluator(SameAsNearestStrategy()).run(
            replace(value, candidate_strategy="missing"), (problem(),)
        )

    decision = DecisionSnapshot.from_decision(NearestStrategy().solve(problem()))
    candidate = replace(decision, strategy="candidate-same")
    observation = ShadowObservation("request-1", decision, candidate, None)
    metrics = ShadowMetrics(1, 1.0, 1.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="sample count"):
        ShadowRun(value, (observation,), replace(metrics, sample_count=2), "a" * 64)
    with pytest.raises(ValueError, match="candidate outcome"):
        ShadowObservation("request-1", decision, candidate, "error")
    with pytest.raises(ValueError, match="promote requires"):
        RegressionAssessment("hold", (), metrics, "a" * 64, "b" * 64)
    with pytest.raises(ValueError, match="unknown regression action"):
        RegressionAssessment(
            cast(RegressionAction, "unknown"), ("reason",), metrics, "a" * 64, "b" * 64
        )
    with pytest.raises(ValueError, match="must not be blank"):
        RegressionAssessment("hold", (" ",), metrics, "a" * 64, "b" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        RegressionAssessment("promote", (), metrics, "short", "b" * 64)
    with pytest.raises(ValueError, match="contain observations"):
        ShadowRun(value, (), metrics, "a" * 64)
    with pytest.raises(ValueError, match="output_digest"):
        ShadowRun(value, (observation,), metrics, "short")
    with pytest.raises(ValueError, match="authoritative decision"):
        ShadowObservation("other", decision, candidate, None)
    with pytest.raises(ValueError, match="candidate decision"):
        ShadowObservation("request-1", decision, replace(candidate, request_id="other"), None)


def test_snapshot_and_metric_validation_reject_inconsistent_values() -> None:
    decision = DecisionSnapshot.from_decision(NearestStrategy().solve(problem()))
    assert decision.deterministic_payload()["courier_id"] == "courier-a"

    with pytest.raises(ValueError, match="score"):
        replace(decision, score=inf)
    with pytest.raises(ValueError, match="latency_millis"):
        replace(decision, latency_millis=-1.0)
    with pytest.raises(ValueError, match="rationale"):
        replace(decision, rationale=(" ",))
    with pytest.raises(ValueError, match="exceeds 16"):
        replace(decision, rationale=tuple(f"reason-{index}" for index in range(17)))
    with pytest.raises(ValueError, match="exceeds 256"):
        replace(decision, strategy="x" * 257)
    with pytest.raises(ValueError, match="sample_count"):
        ShadowMetrics(0, 0.0, 0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="between 0 and 1"):
        ShadowMetrics(1, 1.1, 0.0, 0.0, 0.0)
