"""Manifest-bound planning and retained execution ledger for R3-325."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from typing import Literal

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_power import (
    ProspectivePowerPlan,
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
)
from routemind_compute.application.statistical_routebench_randomness import (
    CommonRandomNumberPlan,
    build_common_random_number_plan,
)

ArmRole = Literal["candidate", "comparator"]
ArmOutcome = Literal[
    "COMPLETED",
    "TIMEOUT",
    "STRATEGY_FAILURE",
    "FALLBACK",
    "HARNESS_DEFECT",
    "INFRASTRUCTURE_DEFECT",
]

_REVISION = re.compile(r"^[0-9a-f]{40}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CAMPAIGN_ID = re.compile(r"^[a-z0-9][a-z0-9-]{7,79}$")
_MATERIAL_SCOPE = "r3_325_material_execution"
_DEFECT_OUTCOMES = {"HARNESS_DEFECT", "INFRASTRUCTURE_DEFECT"}
_SCORED_FAILURES = {"TIMEOUT", "STRATEGY_FAILURE"}


class StatisticalRouteBenchCampaignError(ValueError):
    """Raised when an R3-325 campaign invariant is invalid."""


@dataclass(frozen=True, slots=True)
class CampaignAuthorization:
    implementation_revision: str
    implementation_ci_run: int
    implementation_ci_conclusion: str
    authorized_at_utc: str
    scope: str = _MATERIAL_SCOPE

    def __post_init__(self) -> None:
        if not _REVISION.fullmatch(self.implementation_revision):
            raise StatisticalRouteBenchCampaignError(
                "implementation revision must be a full lowercase Git SHA"
            )
        if (
            not isinstance(self.implementation_ci_run, int)
            or isinstance(self.implementation_ci_run, bool)
            or self.implementation_ci_run <= 0
        ):
            raise StatisticalRouteBenchCampaignError("implementation CI run must be positive")
        if self.implementation_ci_conclusion != "success":
            raise StatisticalRouteBenchCampaignError(
                "material execution requires a successful implementation CI checkpoint"
            )
        if not _UTC.fullmatch(self.authorized_at_utc):
            raise StatisticalRouteBenchCampaignError("authorization time must be UTC RFC 3339")
        if self.scope != _MATERIAL_SCOPE:
            raise StatisticalRouteBenchCampaignError(
                "authorization scope is not R3-325 material execution"
            )

    @property
    def authorization_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "implementation_revision": self.implementation_revision,
            "implementation_ci_run": self.implementation_ci_run,
            "implementation_ci_conclusion": self.implementation_ci_conclusion,
            "authorized_at_utc": self.authorized_at_utc,
            "scope": self.scope,
        }


@dataclass(frozen=True, slots=True)
class CampaignResourceEstimate:
    phase: str
    regime_count: int
    pairs_per_regime: int
    pair_count: int
    arm_runs: int
    threads_per_arm: int
    arm_wall_timeout_seconds: int
    maximum_arm_wall_seconds: int
    expected_peak_memory_mebibytes: int
    maximum_external_artifact_mebibytes: int
    external_cost_usd: float
    disposition: str = "BOUNDED_LOCAL_EXECUTION_WITHIN_FROZEN_ENVELOPE"

    def __post_init__(self) -> None:
        integer_values = (
            self.regime_count,
            self.pairs_per_regime,
            self.pair_count,
            self.arm_runs,
            self.threads_per_arm,
            self.arm_wall_timeout_seconds,
            self.maximum_arm_wall_seconds,
            self.expected_peak_memory_mebibytes,
            self.maximum_external_artifact_mebibytes,
        )
        if self.phase not in {"pilot", "confirmatory"} or any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in integer_values
        ):
            raise StatisticalRouteBenchCampaignError("campaign resource dimensions are invalid")
        if (
            self.pair_count != self.regime_count * self.pairs_per_regime
            or self.arm_runs != self.pair_count * 2
            or self.maximum_arm_wall_seconds != self.arm_runs * self.arm_wall_timeout_seconds
        ):
            raise StatisticalRouteBenchCampaignError("campaign resource arithmetic drifted")
        if (
            not isinstance(self.external_cost_usd, (int, float))
            or isinstance(self.external_cost_usd, bool)
            or not isfinite(self.external_cost_usd)
            or self.external_cost_usd != 0.0
            or self.threads_per_arm != 1
            or self.disposition != "BOUNDED_LOCAL_EXECUTION_WITHIN_FROZEN_ENVELOPE"
        ):
            raise StatisticalRouteBenchCampaignError("campaign escaped its local resource envelope")

    def payload(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "regime_count": self.regime_count,
            "pairs_per_regime": self.pairs_per_regime,
            "pair_count": self.pair_count,
            "arm_runs": self.arm_runs,
            "threads_per_arm": self.threads_per_arm,
            "arm_wall_timeout_seconds": self.arm_wall_timeout_seconds,
            "maximum_arm_wall_seconds": self.maximum_arm_wall_seconds,
            "expected_peak_memory_mebibytes": self.expected_peak_memory_mebibytes,
            "maximum_external_artifact_mebibytes": self.maximum_external_artifact_mebibytes,
            "external_cost_usd": self.external_cost_usd,
            "disposition": self.disposition,
        }


@dataclass(frozen=True, slots=True)
class PilotPairExecutionPlan:
    randomness: CommonRandomNumberPlan
    arm_order: tuple[ArmRole, ArmRole]
    candidate_strategy: str
    comparator_strategy: str
    candidate_parameter_digest: str
    comparator_parameter_digest: str

    def __post_init__(self) -> None:
        expected_order: tuple[ArmRole, ArmRole] = (
            ("candidate", "comparator")
            if self.randomness.pair.replicate % 2 == 0
            else ("comparator", "candidate")
        )
        if self.arm_order != expected_order:
            raise StatisticalRouteBenchCampaignError("pilot arm order escaped parity alternation")
        if not self.candidate_strategy.strip() or not self.comparator_strategy.strip():
            raise StatisticalRouteBenchCampaignError("pilot strategy identities must not be blank")
        if self.candidate_strategy == self.comparator_strategy:
            raise StatisticalRouteBenchCampaignError("pilot arms must use distinct strategies")
        if not _SHA256.fullmatch(self.candidate_parameter_digest) or not _SHA256.fullmatch(
            self.comparator_parameter_digest
        ):
            raise StatisticalRouteBenchCampaignError(
                "pilot parameter digests must be lowercase SHA-256"
            )

    @property
    def pair_plan_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "randomness": self.randomness.payload(),
            "arm_order": self.arm_order,
            "candidate_strategy": self.candidate_strategy,
            "comparator_strategy": self.comparator_strategy,
            "candidate_parameter_digest": self.candidate_parameter_digest,
            "comparator_parameter_digest": self.comparator_parameter_digest,
        }


@dataclass(frozen=True, slots=True)
class StatisticalRouteBenchCampaignPlan:
    campaign_id: str
    protocol_id: str
    protocol_sha256: str
    generator_version: str
    authorization: CampaignAuthorization
    pairs: tuple[PilotPairExecutionPlan, ...]
    resource_estimate: CampaignResourceEstimate
    artifact_relative_root: str
    phase: str = "pilot"
    material_results_present: bool = False
    claim_boundary: str = "PILOT_VARIANCE_INPUT_NOT_CONFIRMATORY_EVIDENCE"
    pilot_ledger_digest: str | None = None
    power_plan_digests: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _CAMPAIGN_ID.fullmatch(self.campaign_id):
            raise StatisticalRouteBenchCampaignError("campaign id is invalid")
        if not self.protocol_id.strip() or not _SHA256.fullmatch(self.protocol_sha256):
            raise StatisticalRouteBenchCampaignError("campaign protocol identity is invalid")
        if self.phase not in {"pilot", "confirmatory"} or self.material_results_present:
            raise StatisticalRouteBenchCampaignError(
                "campaign plan phase or result boundary drifted"
            )
        if self.generator_version != "r3-b-stress-generator-v1":
            raise StatisticalRouteBenchCampaignError("campaign generator boundary drifted")
        if self.phase == "pilot":
            if (
                self.claim_boundary != "PILOT_VARIANCE_INPUT_NOT_CONFIRMATORY_EVIDENCE"
                or self.pilot_ledger_digest is not None
                or self.power_plan_digests
            ):
                raise StatisticalRouteBenchCampaignError("pilot plan claim boundary drifted")
        elif (
            self.claim_boundary != "CONFIRMATORY_EVIDENCE_REQUIRES_FROZEN_STATISTICAL_GATES"
            or self.pilot_ledger_digest is None
            or not _SHA256.fullmatch(self.pilot_ledger_digest)
            or len(self.power_plan_digests) != 16
            or len(set(self.power_plan_digests)) != 16
            or any(not _SHA256.fullmatch(item) for item in self.power_plan_digests)
        ):
            raise StatisticalRouteBenchCampaignError("confirmatory design lineage drifted")
        if self.artifact_relative_root != "experiments/r3/R3-325":
            raise StatisticalRouteBenchCampaignError("campaign artifact root escaped R3-325")
        identities = tuple(
            (
                item.randomness.pair.regime_id,
                item.randomness.pair.replicate,
            )
            for item in self.pairs
        )
        if len(identities) != len(set(identities)):
            raise StatisticalRouteBenchCampaignError("campaign plan contains duplicate pairs")
        if len(self.pairs) != self.resource_estimate.pair_count:
            raise StatisticalRouteBenchCampaignError(
                "campaign pair count escaped resource estimate"
            )
        if any(
            item.randomness.pair.protocol_id != self.protocol_id
            or item.randomness.pair.phase != self.phase
            for item in self.pairs
        ):
            raise StatisticalRouteBenchCampaignError("campaign pair identity escaped its protocol")
        regime_replicates: dict[str, set[int]] = {}
        for item in self.pairs:
            pair = item.randomness.pair
            regime_replicates.setdefault(pair.regime_id, set()).add(pair.replicate)
        replicate_start = 0 if self.phase == "pilot" else 1000
        expected_replicates = set(
            range(replicate_start, replicate_start + self.resource_estimate.pairs_per_regime)
        )
        if len(regime_replicates) != self.resource_estimate.regime_count or any(
            value != expected_replicates for value in regime_replicates.values()
        ):
            raise StatisticalRouteBenchCampaignError(
                "campaign regime or replicate coverage drifted"
            )

    @property
    def plan_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "campaign_id": self.campaign_id,
            "protocol_id": self.protocol_id,
            "protocol_sha256": self.protocol_sha256,
            "generator_version": self.generator_version,
            "authorization": self.authorization.payload(),
            "pairs": [item.payload() for item in self.pairs],
            "resource_estimate": self.resource_estimate.payload(),
            "artifact_relative_root": self.artifact_relative_root,
            "phase": self.phase,
            "material_results_present": self.material_results_present,
            "claim_boundary": self.claim_boundary,
            "pilot_ledger_digest": self.pilot_ledger_digest,
            "power_plan_digests": self.power_plan_digests,
        }


@dataclass(frozen=True, slots=True)
class ArmExecutionAttempt:
    pair_plan_digest: str
    arm_role: ArmRole
    strategy: str
    strategy_version: str
    attempt: int
    outcome: ArmOutcome
    started_at_utc: str
    completed_at_utc: str
    request_count: int | None
    assigned_count: int | None
    scenario_risk_index: float | None
    assignment_rate: float | None
    runtime_millis: float
    strategy_failure_count: int
    fallback_count: int
    timeout_count: int
    event_ids: tuple[str, ...]
    scenario_manifest_digest: str | None
    stream_realization_digests: tuple[tuple[str, str], ...]
    deterministic_result_digest: str
    failure_code: str | None = None

    def __post_init__(self) -> None:
        if not _SHA256.fullmatch(self.pair_plan_digest) or not _SHA256.fullmatch(
            self.deterministic_result_digest
        ):
            raise StatisticalRouteBenchCampaignError("arm execution digests are invalid")
        if not self.strategy.strip() or self.strategy_version != "1.0.0":
            raise StatisticalRouteBenchCampaignError("arm strategy identity drifted")
        if self.attempt not in {1, 2}:
            raise StatisticalRouteBenchCampaignError("arm attempt must be one or two")
        if not _UTC.fullmatch(self.started_at_utc) or not _UTC.fullmatch(self.completed_at_utc):
            raise StatisticalRouteBenchCampaignError("arm timestamps must be UTC RFC 3339")
        if self.runtime_millis < 0:
            raise StatisticalRouteBenchCampaignError("arm runtime must be non-negative")
        if not isfinite(self.runtime_millis) or self.arm_role not in {"candidate", "comparator"}:
            raise StatisticalRouteBenchCampaignError("arm runtime or role is invalid")
        try:
            started = datetime.fromisoformat(self.started_at_utc.replace("Z", "+00:00"))
            completed = datetime.fromisoformat(self.completed_at_utc.replace("Z", "+00:00"))
        except ValueError as error:
            raise StatisticalRouteBenchCampaignError("arm timestamps are invalid") from error
        if started.tzinfo != UTC or completed.tzinfo != UTC or completed < started:
            raise StatisticalRouteBenchCampaignError("arm timestamps are not ordered UTC instants")
        counts = (
            self.strategy_failure_count,
            self.fallback_count,
            self.timeout_count,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts
        ):
            raise StatisticalRouteBenchCampaignError("arm diagnostic counts are invalid")
        if self.outcome in _DEFECT_OUTCOMES:
            if any(
                value is not None
                for value in (
                    self.request_count,
                    self.assigned_count,
                    self.scenario_risk_index,
                    self.assignment_rate,
                )
            ):
                raise StatisticalRouteBenchCampaignError(
                    "harness or infrastructure defects cannot fabricate metrics"
                )
            if not self.failure_code:
                raise StatisticalRouteBenchCampaignError("defect attempts require a failure code")
            if self.event_ids or any(counts):
                raise StatisticalRouteBenchCampaignError(
                    "defect attempts cannot fabricate diagnostics"
                )
            if self.scenario_manifest_digest is not None or self.stream_realization_digests:
                raise StatisticalRouteBenchCampaignError(
                    "defects cannot fabricate scenario lineage"
                )
            return
        if (
            self.request_count is None
            or self.assigned_count is None
            or self.scenario_risk_index is None
            or self.assignment_rate is None
            or self.request_count <= 0
            or not 0 <= self.assigned_count <= self.request_count
            or len(self.event_ids) != self.request_count
            or len(set(self.event_ids)) != len(self.event_ids)
            or not 0.0 <= self.scenario_risk_index <= 1.0
            or not 0.0 <= self.assignment_rate <= 1.0
        ):
            raise StatisticalRouteBenchCampaignError("arm metrics or event identities are invalid")
        if not self.scenario_manifest_digest or not _SHA256.fullmatch(
            self.scenario_manifest_digest
        ):
            raise StatisticalRouteBenchCampaignError("arm scenario manifest digest is invalid")
        if tuple(key for key, _ in self.stream_realization_digests) != (
            "demand",
            "merchant",
            "courier",
            "traffic",
        ) or any(not _SHA256.fullmatch(value) for _, value in self.stream_realization_digests):
            raise StatisticalRouteBenchCampaignError("arm stream realization lineage is invalid")
        if self.assignment_rate != self.assigned_count / self.request_count:
            raise StatisticalRouteBenchCampaignError("arm assignment rate does not match counts")
        if self.outcome not in {"COMPLETED", "TIMEOUT", "STRATEGY_FAILURE", "FALLBACK"}:
            raise StatisticalRouteBenchCampaignError("arm outcome is invalid")
        if self.outcome in _SCORED_FAILURES and (
            self.assigned_count != 0
            or self.scenario_risk_index != 1.0
            or self.assignment_rate != 0.0
            or not self.failure_code
        ):
            raise StatisticalRouteBenchCampaignError(
                "timeout and strategy failure must retain frozen worst-case scoring"
            )
        if self.outcome == "COMPLETED" and self.failure_code is not None:
            raise StatisticalRouteBenchCampaignError("completed arms cannot carry a failure code")
        if self.outcome == "FALLBACK" and self.fallback_count <= 0:
            raise StatisticalRouteBenchCampaignError("fallback arms must retain a fallback count")

    @property
    def is_defect(self) -> bool:
        return self.outcome in _DEFECT_OUTCOMES

    def payload(self) -> dict[str, object]:
        return {
            "pair_plan_digest": self.pair_plan_digest,
            "arm_role": self.arm_role,
            "strategy": self.strategy,
            "strategy_version": self.strategy_version,
            "attempt": self.attempt,
            "outcome": self.outcome,
            "started_at_utc": self.started_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "request_count": self.request_count,
            "assigned_count": self.assigned_count,
            "scenario_risk_index": self.scenario_risk_index,
            "assignment_rate": self.assignment_rate,
            "runtime_millis": self.runtime_millis,
            "strategy_failure_count": self.strategy_failure_count,
            "fallback_count": self.fallback_count,
            "timeout_count": self.timeout_count,
            "event_ids": self.event_ids,
            "scenario_manifest_digest": self.scenario_manifest_digest,
            "stream_realization_digests": self.stream_realization_digests,
            "deterministic_result_digest": self.deterministic_result_digest,
            "failure_code": self.failure_code,
        }


@dataclass(frozen=True, slots=True)
class PairExecutionRecord:
    pair_plan: PilotPairExecutionPlan
    attempts: tuple[ArmExecutionAttempt, ...]

    def __post_init__(self) -> None:
        if not self.attempts:
            raise StatisticalRouteBenchCampaignError("pair execution must retain attempts")
        if any(item.pair_plan_digest != self.pair_plan.pair_plan_digest for item in self.attempts):
            raise StatisticalRouteBenchCampaignError("arm attempt escaped its pair plan")
        if any(item.arm_role not in self.pair_plan.arm_order for item in self.attempts):
            raise StatisticalRouteBenchCampaignError("unexpected arm role entered pair execution")
        for role in self.pair_plan.arm_order:
            role_attempts = tuple(item for item in self.attempts if item.arm_role == role)
            if not 1 <= len(role_attempts) <= 2:
                raise StatisticalRouteBenchCampaignError("each arm must retain one or two attempts")
            if tuple(item.attempt for item in role_attempts) != tuple(
                range(1, len(role_attempts) + 1)
            ):
                raise StatisticalRouteBenchCampaignError("arm attempt sequence is invalid")
            if len(role_attempts) == 2 and not role_attempts[0].is_defect:
                raise StatisticalRouteBenchCampaignError("only a retained defect may be retried")
        expected_sequence = tuple(
            role
            for role in self.pair_plan.arm_order
            for _ in range(sum(item.arm_role == role for item in self.attempts))
        )
        if tuple(item.arm_role for item in self.attempts) != expected_sequence:
            raise StatisticalRouteBenchCampaignError("arm attempts escaped frozen execution order")
        terminal = {
            role: tuple(item for item in self.attempts if item.arm_role == role)[-1]
            for role in self.pair_plan.arm_order
        }
        for role, attempt in terminal.items():
            expected_strategy = (
                self.pair_plan.candidate_strategy
                if role == "candidate"
                else self.pair_plan.comparator_strategy
            )
            if attempt.strategy != expected_strategy:
                raise StatisticalRouteBenchCampaignError("arm strategy escaped its frozen role")
        complete_attempts = tuple(item for item in terminal.values() if not item.is_defect)
        if complete_attempts and any(
            item.scenario_manifest_digest != complete_attempts[0].scenario_manifest_digest
            or item.stream_realization_digests != complete_attempts[0].stream_realization_digests
            for item in complete_attempts[1:]
        ):
            raise StatisticalRouteBenchCampaignError(
                "paired arms did not share realized randomness"
            )

    @property
    def complete(self) -> bool:
        return all(
            not tuple(item for item in self.attempts if item.arm_role == role)[-1].is_defect
            for role in self.pair_plan.arm_order
        )

    @property
    def record_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "pair_plan": self.pair_plan.payload(),
            "attempts": [item.payload() for item in self.attempts],
            "complete": self.complete,
        }


@dataclass(frozen=True, slots=True)
class StatisticalRouteBenchCampaignLedger:
    plan_digest: str
    records: tuple[PairExecutionRecord, ...]
    retained_attempt_count: int
    complete_pair_count: int
    outcome_counts: tuple[tuple[str, int], ...]
    disposition: str
    phase: str = "pilot"
    claim_boundary: str = "PILOT_VARIANCE_INPUT_NOT_CONFIRMATORY_EVIDENCE"

    def __post_init__(self) -> None:
        if not _SHA256.fullmatch(self.plan_digest):
            raise StatisticalRouteBenchCampaignError("ledger plan digest is invalid")
        if len({item.pair_plan.pair_plan_digest for item in self.records}) != len(self.records):
            raise StatisticalRouteBenchCampaignError("ledger contains duplicate pair records")
        retained = sum(len(item.attempts) for item in self.records)
        complete = sum(item.complete for item in self.records)
        outcomes = Counter(
            attempt.outcome for record in self.records for attempt in record.attempts
        )
        if self.phase not in {"pilot", "confirmatory"}:
            raise StatisticalRouteBenchCampaignError("ledger phase is invalid")
        expected_disposition = _ledger_disposition(
            self.phase, complete == len(self.records) and bool(self.records)
        )
        expected_claim = (
            "PILOT_VARIANCE_INPUT_NOT_CONFIRMATORY_EVIDENCE"
            if self.phase == "pilot"
            else "CONFIRMATORY_EVIDENCE_REQUIRES_FROZEN_STATISTICAL_GATES"
        )
        if (
            self.retained_attempt_count != retained
            or self.complete_pair_count != complete
            or self.outcome_counts != tuple(sorted(outcomes.items()))
            or self.disposition != expected_disposition
            or self.claim_boundary != expected_claim
        ):
            raise StatisticalRouteBenchCampaignError("ledger summary or claim boundary drifted")

    @property
    def ledger_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "plan_digest": self.plan_digest,
            "records": [item.payload() for item in self.records],
            "retained_attempt_count": self.retained_attempt_count,
            "complete_pair_count": self.complete_pair_count,
            "outcome_counts": self.outcome_counts,
            "disposition": self.disposition,
            "phase": self.phase,
            "claim_boundary": self.claim_boundary,
        }


ArmExecutor = Callable[[PilotPairExecutionPlan, ArmRole, int], ArmExecutionAttempt]


def build_pilot_campaign_plan(
    protocol: StatisticalRouteBenchProtocol,
    campaign_id: str,
    authorization: CampaignAuthorization,
) -> StatisticalRouteBenchCampaignPlan:
    candidate_digest = canonical_digest(dict(protocol.candidate.parameters))
    comparator_digest = canonical_digest(dict(protocol.comparator.parameters))
    pairs = tuple(
        PilotPairExecutionPlan(
            randomness=build_common_random_number_plan(protocol, "pilot", regime_id, replicate),
            arm_order=(
                ("candidate", "comparator") if replicate % 2 == 0 else ("comparator", "candidate")
            ),
            candidate_strategy=protocol.candidate.strategy,
            comparator_strategy=protocol.comparator.strategy,
            candidate_parameter_digest=candidate_digest,
            comparator_parameter_digest=comparator_digest,
        )
        for regime_id in protocol.regime_ids
        for replicate in range(protocol.pilot_replicates_per_regime)
    )
    resources = protocol.resource_envelope
    arm_runs = len(pairs) * 2
    if arm_runs != resources.pilot_arm_runs:
        raise StatisticalRouteBenchCampaignError("pilot arm count drifted from resource envelope")
    estimate = CampaignResourceEstimate(
        phase="pilot",
        regime_count=len(protocol.regime_ids),
        pairs_per_regime=protocol.pilot_replicates_per_regime,
        pair_count=len(pairs),
        arm_runs=arm_runs,
        threads_per_arm=resources.threads_per_arm,
        arm_wall_timeout_seconds=resources.arm_wall_timeout_seconds,
        maximum_arm_wall_seconds=arm_runs * resources.arm_wall_timeout_seconds,
        expected_peak_memory_mebibytes=resources.expected_peak_memory_mebibytes,
        maximum_external_artifact_mebibytes=resources.maximum_external_artifact_mebibytes,
        external_cost_usd=resources.external_cost_usd,
    )
    return StatisticalRouteBenchCampaignPlan(
        campaign_id=campaign_id,
        protocol_id=protocol.protocol_id,
        protocol_sha256=protocol.manifest_sha256,
        generator_version=protocol.scenario_design.generator_version,
        authorization=authorization,
        pairs=pairs,
        resource_estimate=estimate,
        artifact_relative_root=protocol.artifact_relative_root,
    )


def build_confirmatory_campaign_plan(
    protocol: StatisticalRouteBenchProtocol,
    campaign_id: str,
    authorization: CampaignAuthorization,
    pilot_ledger_digest: str,
    power_plans: tuple[ProspectivePowerPlan, ...],
) -> StatisticalRouteBenchCampaignPlan:
    expected = {
        (regime_id, metric_id)
        for regime_id in protocol.regime_ids
        for metric_id in ("assignment_rate", "scenario_risk_index")
    }
    actual = {(item.regime_id, item.metric_id) for item in power_plans}
    if len(power_plans) != len(expected) or actual != expected:
        raise StatisticalRouteBenchCampaignError(
            "confirmatory power plans must cover the frozen 16-test family"
        )
    if any(
        item.protocol_id != protocol.protocol_id
        or not item.observed_pilot
        or item.planned_pair_count > protocol.maximum_confirmatory_pairs_per_regime
        for item in power_plans
    ):
        raise StatisticalRouteBenchCampaignError("confirmatory power plan identity drifted")
    pair_count = max(item.planned_pair_count for item in power_plans)
    candidate_digest = canonical_digest(dict(protocol.candidate.parameters))
    comparator_digest = canonical_digest(dict(protocol.comparator.parameters))
    pairs = tuple(
        PilotPairExecutionPlan(
            randomness=build_common_random_number_plan(
                protocol,
                "confirmatory",
                regime_id,
                protocol.confirmatory_replicate_start + offset,
            ),
            arm_order=(
                ("candidate", "comparator")
                if (protocol.confirmatory_replicate_start + offset) % 2 == 0
                else ("comparator", "candidate")
            ),
            candidate_strategy=protocol.candidate.strategy,
            comparator_strategy=protocol.comparator.strategy,
            candidate_parameter_digest=candidate_digest,
            comparator_parameter_digest=comparator_digest,
        )
        for regime_id in protocol.regime_ids
        for offset in range(pair_count)
    )
    resources = protocol.resource_envelope
    arm_runs = len(pairs) * 2
    if arm_runs > resources.maximum_confirmatory_arm_runs:
        raise StatisticalRouteBenchCampaignError(
            "confirmatory campaign exceeds its frozen arm-run envelope"
        )
    estimate = CampaignResourceEstimate(
        phase="confirmatory",
        regime_count=len(protocol.regime_ids),
        pairs_per_regime=pair_count,
        pair_count=len(pairs),
        arm_runs=arm_runs,
        threads_per_arm=resources.threads_per_arm,
        arm_wall_timeout_seconds=resources.arm_wall_timeout_seconds,
        maximum_arm_wall_seconds=arm_runs * resources.arm_wall_timeout_seconds,
        expected_peak_memory_mebibytes=resources.expected_peak_memory_mebibytes,
        maximum_external_artifact_mebibytes=resources.maximum_external_artifact_mebibytes,
        external_cost_usd=resources.external_cost_usd,
    )
    return StatisticalRouteBenchCampaignPlan(
        campaign_id=campaign_id,
        protocol_id=protocol.protocol_id,
        protocol_sha256=protocol.manifest_sha256,
        generator_version=protocol.scenario_design.generator_version,
        authorization=authorization,
        pairs=pairs,
        resource_estimate=estimate,
        artifact_relative_root=protocol.artifact_relative_root,
        phase="confirmatory",
        claim_boundary="CONFIRMATORY_EVIDENCE_REQUIRES_FROZEN_STATISTICAL_GATES",
        pilot_ledger_digest=pilot_ledger_digest,
        power_plan_digests=tuple(sorted(item.plan_digest for item in power_plans)),
    )


def execute_campaign(
    plan: StatisticalRouteBenchCampaignPlan,
    executor: ArmExecutor,
) -> StatisticalRouteBenchCampaignLedger:
    records: list[PairExecutionRecord] = []
    outcomes: Counter[str] = Counter()
    for pair in plan.pairs:
        attempts: list[ArmExecutionAttempt] = []
        for role in pair.arm_order:
            first = _validated_attempt(pair, role, 1, executor(pair, role, 1))
            attempts.append(first)
            outcomes[first.outcome] += 1
            if first.is_defect:
                retry = _validated_attempt(pair, role, 2, executor(pair, role, 2))
                attempts.append(retry)
                outcomes[retry.outcome] += 1
        records.append(PairExecutionRecord(pair, tuple(attempts)))
    complete = sum(item.complete for item in records)
    complete_campaign = complete == len(plan.pairs)
    return StatisticalRouteBenchCampaignLedger(
        plan_digest=plan.plan_digest,
        records=tuple(records),
        retained_attempt_count=sum(len(item.attempts) for item in records),
        complete_pair_count=complete,
        outcome_counts=tuple(sorted(outcomes.items())),
        disposition=_ledger_disposition(plan.phase, complete_campaign),
        phase=plan.phase,
        claim_boundary=plan.claim_boundary,
    )


def execute_pilot_campaign(
    plan: StatisticalRouteBenchCampaignPlan,
    executor: ArmExecutor,
) -> StatisticalRouteBenchCampaignLedger:
    if plan.phase != "pilot":
        raise StatisticalRouteBenchCampaignError("pilot executor requires a pilot plan")
    return execute_campaign(plan, executor)


def execute_campaign_pair(
    pair: PilotPairExecutionPlan,
    executor: ArmExecutor,
) -> PairExecutionRecord:
    attempts: list[ArmExecutionAttempt] = []
    for role in pair.arm_order:
        first = _validated_attempt(pair, role, 1, executor(pair, role, 1))
        attempts.append(first)
        if first.is_defect:
            attempts.append(_validated_attempt(pair, role, 2, executor(pair, role, 2)))
    return PairExecutionRecord(pair, tuple(attempts))


def summarize_campaign_records(
    plan: StatisticalRouteBenchCampaignPlan,
    records: tuple[PairExecutionRecord, ...],
) -> StatisticalRouteBenchCampaignLedger:
    if tuple(item.pair_plan for item in records) != plan.pairs:
        raise StatisticalRouteBenchCampaignError("campaign records do not cover the plan in order")
    outcomes = Counter(attempt.outcome for record in records for attempt in record.attempts)
    complete = sum(item.complete for item in records)
    return StatisticalRouteBenchCampaignLedger(
        plan_digest=plan.plan_digest,
        records=records,
        retained_attempt_count=sum(len(item.attempts) for item in records),
        complete_pair_count=complete,
        outcome_counts=tuple(sorted(outcomes.items())),
        disposition=_ledger_disposition(plan.phase, complete == len(records)),
        phase=plan.phase,
        claim_boundary=plan.claim_boundary,
    )


def _ledger_disposition(phase: str, complete: bool) -> str:
    if not complete:
        return f"{phase.upper()}_INCOMPLETE_RETAIN_ALL_OUTPUTS"
    if phase == "pilot":
        return "PILOT_COMPLETE_FOR_VARIANCE_ONLY"
    return "CONFIRMATORY_COMPLETE_FOR_FROZEN_ANALYSIS"


def _validated_attempt(
    pair: PilotPairExecutionPlan,
    role: ArmRole,
    attempt: int,
    observation: ArmExecutionAttempt,
) -> ArmExecutionAttempt:
    expected_strategy = pair.candidate_strategy if role == "candidate" else pair.comparator_strategy
    if (
        observation.pair_plan_digest != pair.pair_plan_digest
        or observation.arm_role != role
        or observation.strategy != expected_strategy
        or observation.attempt != attempt
    ):
        raise StatisticalRouteBenchCampaignError("executor returned drifted arm identity")
    return observation


__all__ = [
    "ArmExecutionAttempt",
    "ArmExecutor",
    "ArmOutcome",
    "ArmRole",
    "CampaignAuthorization",
    "CampaignResourceEstimate",
    "PairExecutionRecord",
    "PilotPairExecutionPlan",
    "StatisticalRouteBenchCampaignError",
    "StatisticalRouteBenchCampaignLedger",
    "StatisticalRouteBenchCampaignPlan",
    "build_confirmatory_campaign_plan",
    "build_pilot_campaign_plan",
    "execute_campaign",
    "execute_campaign_pair",
    "execute_pilot_campaign",
    "summarize_campaign_records",
]
