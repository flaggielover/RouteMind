from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

Metadata = tuple[tuple[str, str], ...]
HealthChecks = tuple[tuple[str, bool], ...]
DecisionKind = Literal["promote", "hold", "rollback"]
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _text(value: str) -> str:
    return value.strip()


def _digest(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _metadata(values: Metadata) -> Metadata:
    normalized = tuple(sorted((_text(key), _text(value)) for key, value in values))
    if any(not key or not value for key, value in normalized):
        raise ValueError("metadata entries must not be blank")
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("metadata keys must be unique")
    return normalized


def _health_checks(values: HealthChecks) -> HealthChecks:
    normalized = tuple(sorted(((_text(key), bool(value)) for key, value in values), key=lambda item: item[0]))
    if any(not key for key, _ in normalized):
        raise ValueError("health check identifiers must not be blank")
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("health check identifiers must be unique")
    return normalized


def _content_digest(value: str, name: str) -> str:
    normalized = _text(value)
    if not _DIGEST.fullmatch(normalized):
        raise ValueError(f"{name} must be a lowercase content digest")
    return normalized


@dataclass(frozen=True, slots=True)
class ReleaseStage:
    stage_id: str
    traffic_bps: int
    min_samples: int
    soak_seconds: int
    max_error_bps: int
    max_regression_bps: int
    max_disagreement_bps: int
    required_health_checks: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_id", _text(self.stage_id))
        checks = tuple(sorted({_text(value) for value in self.required_health_checks}))
        object.__setattr__(self, "required_health_checks", checks)
        if not self.stage_id:
            raise ValueError("stage_id must not be blank")
        if not checks or any(not check for check in checks):
            raise ValueError("required health checks must not be blank")
        if not 1 <= self.traffic_bps <= 10_000:
            raise ValueError("traffic_bps must be between 1 and 10000")
        if self.min_samples <= 0 or self.soak_seconds <= 0:
            raise ValueError("minimum samples and soak seconds must be positive")
        for value, name in (
            (self.max_error_bps, "max_error_bps"),
            (self.max_regression_bps, "max_regression_bps"),
            (self.max_disagreement_bps, "max_disagreement_bps"),
        ):
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be between 0 and 10000")

    def payload(self) -> dict[str, object]:
        return {
            "stage_id": self.stage_id,
            "traffic_bps": self.traffic_bps,
            "min_samples": self.min_samples,
            "soak_seconds": self.soak_seconds,
            "max_error_bps": self.max_error_bps,
            "max_regression_bps": self.max_regression_bps,
            "max_disagreement_bps": self.max_disagreement_bps,
            "required_health_checks": self.required_health_checks,
        }


@dataclass(frozen=True, slots=True)
class StagePlan:
    active_release_digest: str
    candidate_release_digest: str
    rollback_package_digest: str
    policy_version: str
    stages: tuple[ReleaseStage, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "active_release_digest", _content_digest(self.active_release_digest, "active_release_digest"))
        object.__setattr__(self, "candidate_release_digest", _content_digest(self.candidate_release_digest, "candidate_release_digest"))
        object.__setattr__(self, "rollback_package_digest", _content_digest(self.rollback_package_digest, "rollback_package_digest"))
        object.__setattr__(self, "policy_version", _text(self.policy_version))
        object.__setattr__(self, "stages", tuple(sorted(self.stages, key=lambda stage: stage.traffic_bps)))
        if not self.policy_version:
            raise ValueError("policy_version must not be blank")
        if not self.stages:
            raise ValueError("stages must not be empty")
        identifiers = [stage.stage_id for stage in self.stages]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("stage identifiers must be unique")
        allocations = [stage.traffic_bps for stage in self.stages]
        if allocations != sorted(allocations) or any(left >= right for left, right in zip(allocations, allocations[1:])):
            raise ValueError("traffic allocations must strictly increase")
        if allocations[-1] != 10_000:
            raise ValueError("final stage must allocate 10000 basis points")

    def payload(self) -> dict[str, object]:
        return {
            "active_release_digest": self.active_release_digest,
            "candidate_release_digest": self.candidate_release_digest,
            "rollback_package_digest": self.rollback_package_digest,
            "policy_version": self.policy_version,
            "stages": [stage.payload() for stage in self.stages],
        }

    @property
    def digest(self) -> str:
        return _digest(self.payload())


@dataclass(frozen=True, slots=True)
class StageObservation:
    stage_id: str
    samples: int
    soak_seconds: int
    error_bps: int
    regression_bps: int
    disagreement_bps: int
    health_checks: HealthChecks
    rollback_ready: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_id", _text(self.stage_id))
        object.__setattr__(self, "health_checks", _health_checks(self.health_checks))
        if not self.stage_id:
            raise ValueError("stage_id must not be blank")
        if self.samples < 0 or self.soak_seconds < 0:
            raise ValueError("samples and soak_seconds must be non-negative")
        for value, name in (
            (self.error_bps, "error_bps"),
            (self.regression_bps, "regression_bps"),
            (self.disagreement_bps, "disagreement_bps"),
        ):
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be between 0 and 10000")

    def payload(self) -> dict[str, object]:
        return {
            "stage_id": self.stage_id,
            "samples": self.samples,
            "soak_seconds": self.soak_seconds,
            "error_bps": self.error_bps,
            "regression_bps": self.regression_bps,
            "disagreement_bps": self.disagreement_bps,
            "health_checks": self.health_checks,
            "rollback_ready": self.rollback_ready,
        }


@dataclass(frozen=True, slots=True)
class StageDecision:
    decision: DecisionKind
    stage_id: str
    next_stage_id: str | None
    reasons: tuple[str, ...]
    plan_digest: str
    observation_digest: str

    def __post_init__(self) -> None:
        if self.decision not in ("promote", "hold", "rollback"):
            raise ValueError("unknown stage decision")
        if not self.reasons:
            raise ValueError("decision requires reasons")
        if not _DIGEST.fullmatch(self.plan_digest) or not _DIGEST.fullmatch(self.observation_digest):
            raise ValueError("decision digests must be lowercase content digests")

    @property
    def digest(self) -> str:
        return _digest(
            {
                "decision": self.decision,
                "stage_id": self.stage_id,
                "next_stage_id": self.next_stage_id,
                "reasons": self.reasons,
                "plan_digest": self.plan_digest,
                "observation_digest": self.observation_digest,
            }
        )


def evaluate_stage(plan: StagePlan, observation: StageObservation) -> StageDecision:
    stages = {stage.stage_id: (index, stage) for index, stage in enumerate(plan.stages)}
    if observation.stage_id not in stages:
        return StageDecision(
            "rollback",
            observation.stage_id,
            None,
            (f"unknown_stage:{observation.stage_id}",),
            plan.digest,
            _digest(observation.payload()),
        )

    index, stage = stages[observation.stage_id]
    reasons: list[str] = []
    checks = dict(observation.health_checks)
    if not observation.rollback_ready:
        reasons.append("rollback_not_ready")
    for required in stage.required_health_checks:
        if required not in checks:
            reasons.append(f"health_check_missing:{required}")
        elif not checks[required]:
            reasons.append(f"health_check_unhealthy:{required}")
    if observation.error_bps >= stage.max_error_bps:
        reasons.append(f"error_threshold:{observation.error_bps}>={stage.max_error_bps}")
    if observation.regression_bps >= stage.max_regression_bps:
        reasons.append(f"regression_threshold:{observation.regression_bps}>={stage.max_regression_bps}")
    if observation.disagreement_bps >= stage.max_disagreement_bps:
        reasons.append(f"disagreement_threshold:{observation.disagreement_bps}>={stage.max_disagreement_bps}")

    if reasons:
        decision: DecisionKind = "rollback"
        next_stage_id = None
    else:
        hold_reasons: list[str] = []
        if observation.samples < stage.min_samples:
            hold_reasons.append(f"samples_incomplete:{observation.samples}<{stage.min_samples}")
        if observation.soak_seconds < stage.soak_seconds:
            hold_reasons.append(f"soak_incomplete:{observation.soak_seconds}<{stage.soak_seconds}")
        if hold_reasons:
            decision = "hold"
            reasons = hold_reasons
            next_stage_id = None
        else:
            decision = "promote"
            next_stage_id = plan.stages[index + 1].stage_id if index + 1 < len(plan.stages) else None
            reasons = ("stage_complete",) if next_stage_id is None else (f"advance_to:{next_stage_id}",)

    return StageDecision(
        decision,
        observation.stage_id,
        next_stage_id,
        tuple(reasons),
        plan.digest,
        _digest(observation.payload()),
    )
