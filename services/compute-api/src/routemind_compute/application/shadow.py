from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import Literal

from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.domain.dispatch import DispatchDecision, DispatchProblem

Metadata = tuple[tuple[str, str], ...]
RegressionAction = Literal["promote", "hold"]

MAX_METADATA_ITEMS = 32
MAX_RATIONALE_ITEMS = 16
MAX_TEXT_LENGTH = 256


def _validate_text(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank")
    if len(normalized) > MAX_TEXT_LENGTH:
        raise ValueError(f"{name} exceeds {MAX_TEXT_LENGTH} characters")
    return normalized


def _normalize_metadata(values: Metadata) -> Metadata:
    if len(values) > MAX_METADATA_ITEMS:
        raise ValueError(f"metadata exceeds {MAX_METADATA_ITEMS} items")
    normalized = tuple(
        sorted(
            (_validate_text(key, "metadata key"), _validate_text(value, "metadata value"))
            for key, value in values
        )
    )
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("metadata keys must be unique")
    return normalized


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(payload: object) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _validate_rate(value: float, name: str) -> None:
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be finite and between 0 and 1")


@dataclass(frozen=True, slots=True)
class RegressionPolicy:
    minimum_samples: int = 1
    maximum_failure_rate: float = 0.0
    maximum_assignment_rate_drop: float = 0.0
    maximum_disagreement_rate: float = 1.0

    def __post_init__(self) -> None:
        if self.minimum_samples <= 0:
            raise ValueError("minimum_samples must be positive")
        _validate_rate(self.maximum_failure_rate, "maximum_failure_rate")
        _validate_rate(self.maximum_assignment_rate_drop, "maximum_assignment_rate_drop")
        _validate_rate(self.maximum_disagreement_rate, "maximum_disagreement_rate")

    def payload(self) -> dict[str, object]:
        return {
            "minimum_samples": self.minimum_samples,
            "maximum_failure_rate": self.maximum_failure_rate,
            "maximum_assignment_rate_drop": self.maximum_assignment_rate_drop,
            "maximum_disagreement_rate": self.maximum_disagreement_rate,
        }


@dataclass(frozen=True, slots=True)
class ShadowManifest:
    manifest_id: str
    code_version: str
    scenario_id: str
    seed: int
    active_strategy: str
    candidate_strategy: str
    policy: RegressionPolicy
    configuration: Metadata = ()

    def __post_init__(self) -> None:
        for field_name in (
            "manifest_id",
            "code_version",
            "scenario_id",
            "active_strategy",
            "candidate_strategy",
        ):
            object.__setattr__(
                self, field_name, _validate_text(getattr(self, field_name), field_name)
            )
        if self.active_strategy == self.candidate_strategy:
            raise ValueError("active and candidate strategies must differ")
        object.__setattr__(self, "configuration", _normalize_metadata(self.configuration))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "code_version": self.code_version,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "active_strategy": self.active_strategy,
            "candidate_strategy": self.candidate_strategy,
            "policy": self.policy.payload(),
            "configuration": self.configuration,
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class DecisionSnapshot:
    request_id: str
    strategy: str
    strategy_version: str
    courier_id: str | None
    score: float | None
    rationale: tuple[str, ...]
    latency_millis: float

    def __post_init__(self) -> None:
        for value, name in (
            (self.request_id, "request_id"),
            (self.strategy, "strategy"),
            (self.strategy_version, "strategy_version"),
        ):
            _validate_text(value, name)
        if self.courier_id is not None:
            _validate_text(self.courier_id, "courier_id")
        if self.score is not None and not isfinite(self.score):
            raise ValueError("score must be finite")
        if not isfinite(self.latency_millis) or self.latency_millis < 0:
            raise ValueError("latency_millis must be finite and non-negative")
        if len(self.rationale) > MAX_RATIONALE_ITEMS:
            raise ValueError(f"rationale exceeds {MAX_RATIONALE_ITEMS} items")
        object.__setattr__(
            self,
            "rationale",
            tuple(_validate_text(item, "rationale item") for item in self.rationale),
        )

    @classmethod
    def from_decision(cls, decision: DispatchDecision) -> DecisionSnapshot:
        return cls(
            decision.request_id,
            decision.strategy,
            decision.strategy_version,
            decision.courier_id,
            decision.score,
            decision.rationale,
            decision.latency_millis,
        )

    def deterministic_payload(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "strategy": self.strategy,
            "strategy_version": self.strategy_version,
            "courier_id": self.courier_id,
            "score": self.score,
            "rationale": self.rationale,
        }

    def observed_payload(self) -> dict[str, object]:
        return {**self.deterministic_payload(), "latency_millis": self.latency_millis}


@dataclass(frozen=True, slots=True)
class ShadowObservation:
    request_id: str
    authoritative: DecisionSnapshot
    candidate: DecisionSnapshot | None
    candidate_error: str | None

    def __post_init__(self) -> None:
        _validate_text(self.request_id, "request_id")
        if self.authoritative.request_id != self.request_id:
            raise ValueError("authoritative decision request does not match observation")
        if (self.candidate is None) == (self.candidate_error is None):
            raise ValueError("observation requires exactly one candidate outcome")
        if self.candidate is not None and self.candidate.request_id != self.request_id:
            raise ValueError("candidate decision request does not match observation")
        if self.candidate_error is not None:
            object.__setattr__(
                self, "candidate_error", _validate_text(self.candidate_error, "candidate_error")
            )

    @property
    def disagrees(self) -> bool:
        return self.candidate is None or (
            self.candidate.courier_id != self.authoritative.courier_id
        )

    def deterministic_payload(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "authoritative": self.authoritative.deterministic_payload(),
            "candidate": self.candidate.deterministic_payload() if self.candidate else None,
            "candidate_error": self.candidate_error,
            "disagrees": self.disagrees,
        }

    def observed_payload(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "authoritative": self.authoritative.observed_payload(),
            "candidate": self.candidate.observed_payload() if self.candidate else None,
            "candidate_error": self.candidate_error,
            "disagrees": self.disagrees,
        }


@dataclass(frozen=True, slots=True)
class ShadowMetrics:
    sample_count: int
    active_assignment_rate: float
    candidate_assignment_rate: float
    candidate_failure_rate: float
    disagreement_rate: float

    def __post_init__(self) -> None:
        if self.sample_count <= 0:
            raise ValueError("sample_count must be positive")
        for value, name in (
            (self.active_assignment_rate, "active_assignment_rate"),
            (self.candidate_assignment_rate, "candidate_assignment_rate"),
            (self.candidate_failure_rate, "candidate_failure_rate"),
            (self.disagreement_rate, "disagreement_rate"),
        ):
            _validate_rate(value, name)

    @property
    def assignment_rate_drop(self) -> float:
        return self.active_assignment_rate - self.candidate_assignment_rate

    def payload(self) -> dict[str, object]:
        return {
            "sample_count": self.sample_count,
            "active_assignment_rate": self.active_assignment_rate,
            "candidate_assignment_rate": self.candidate_assignment_rate,
            "candidate_failure_rate": self.candidate_failure_rate,
            "disagreement_rate": self.disagreement_rate,
            "assignment_rate_drop": self.assignment_rate_drop,
        }


@dataclass(frozen=True, slots=True)
class ShadowRun:
    manifest: ShadowManifest
    observations: tuple[ShadowObservation, ...]
    metrics: ShadowMetrics
    output_digest: str

    def __post_init__(self) -> None:
        if not self.observations:
            raise ValueError("shadow run must contain observations")
        if len(self.observations) != self.metrics.sample_count:
            raise ValueError("shadow metrics sample count does not match observations")
        if len(self.output_digest) != 64:
            raise ValueError("output_digest must be a SHA-256 digest")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "manifest": self.manifest.canonical_payload(),
            "observations": [item.deterministic_payload() for item in self.observations],
            "metrics": self.metrics.payload(),
            "output_digest": self.output_digest,
        }

    def observed_payload(self) -> dict[str, object]:
        return {
            "manifest": self.manifest.canonical_payload(),
            "observations": [item.observed_payload() for item in self.observations],
            "metrics": self.metrics.payload(),
            "output_digest": self.output_digest,
        }


class ShadowModeEvaluator:
    def __init__(self, registry: StrategyRegistry) -> None:
        self.registry = registry

    def run(self, manifest: ShadowManifest, problems: tuple[DispatchProblem, ...]) -> ShadowRun:
        if not problems:
            raise ValueError("shadow run requires at least one problem")
        request_ids = [problem.request_id for problem in problems]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("shadow problem request identifiers must be unique")
        self.registry.get(manifest.active_strategy)
        self.registry.get(manifest.candidate_strategy)
        observations = tuple(
            self._observe(manifest, problem)
            for problem in sorted(problems, key=lambda item: item.request_id)
        )
        sample_count = len(observations)
        active_assigned = sum(item.authoritative.courier_id is not None for item in observations)
        candidate_assigned = sum(
            item.candidate is not None and item.candidate.courier_id is not None
            for item in observations
        )
        candidate_failures = sum(item.candidate is None for item in observations)
        disagreements = sum(item.disagrees for item in observations)
        metrics = ShadowMetrics(
            sample_count,
            active_assigned / sample_count,
            candidate_assigned / sample_count,
            candidate_failures / sample_count,
            disagreements / sample_count,
        )
        deterministic = {
            "manifest_digest": manifest.digest,
            "observations": [item.deterministic_payload() for item in observations],
            "metrics": metrics.payload(),
        }
        return ShadowRun(manifest, observations, metrics, _digest(deterministic))

    def _observe(self, manifest: ShadowManifest, problem: DispatchProblem) -> ShadowObservation:
        authoritative = DecisionSnapshot.from_decision(
            self.registry.solve(manifest.active_strategy, problem)
        )
        try:
            candidate = DecisionSnapshot.from_decision(
                self.registry.solve(manifest.candidate_strategy, problem)
            )
        except Exception as error:
            failure = f"candidate_execution_failed:{type(error).__name__}"
            return ShadowObservation(problem.request_id, authoritative, None, failure)
        return ShadowObservation(problem.request_id, authoritative, candidate, None)


@dataclass(frozen=True, slots=True)
class RegressionAssessment:
    action: RegressionAction
    reasons: tuple[str, ...]
    metrics: ShadowMetrics
    manifest_digest: str
    run_digest: str

    def __post_init__(self) -> None:
        if self.action not in ("promote", "hold"):
            raise ValueError("unknown regression action")
        if (self.action == "promote") == bool(self.reasons):
            raise ValueError("promote requires no reasons and hold requires reasons")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("regression reasons must not be blank")
        if len(self.manifest_digest) != 64 or len(self.run_digest) != 64:
            raise ValueError("assessment digests must be SHA-256 digests")

    def payload(self) -> dict[str, object]:
        return {
            "action": self.action,
            "reasons": self.reasons,
            "metrics": self.metrics.payload(),
            "manifest_digest": self.manifest_digest,
            "run_digest": self.run_digest,
        }


class RegressionGate:
    def assess(self, run: ShadowRun) -> RegressionAssessment:
        policy = run.manifest.policy
        metrics = run.metrics
        reasons: list[str] = []
        if metrics.sample_count < policy.minimum_samples:
            reasons.append("insufficient_samples")
        if metrics.candidate_failure_rate > policy.maximum_failure_rate:
            reasons.append("candidate_failure_rate_exceeded")
        if metrics.assignment_rate_drop > policy.maximum_assignment_rate_drop:
            reasons.append("assignment_rate_drop_exceeded")
        if metrics.disagreement_rate > policy.maximum_disagreement_rate:
            reasons.append("disagreement_rate_exceeded")
        action: RegressionAction = "hold" if reasons else "promote"
        return RegressionAssessment(
            action,
            tuple(reasons),
            metrics,
            run.manifest.digest,
            run.output_digest,
        )
