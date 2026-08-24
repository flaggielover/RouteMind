"""Frozen pilot-to-power transition for the R3-325 campaign."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_campaign import (
    ArmExecutionAttempt,
    PairExecutionRecord,
    StatisticalRouteBenchCampaignLedger,
    StatisticalRouteBenchCampaignPlan,
)
from routemind_compute.application.statistical_routebench_estimation import (
    PairedEstimate,
    PairedEstimationError,
    PairedMetricSpec,
    PairedObservation,
    estimate_paired,
)
from routemind_compute.application.statistical_routebench_power import (
    PilotVarianceInput,
    ProspectivePowerError,
    ProspectivePowerPlan,
    plan_primary_power,
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
)

PlanningStatus = Literal["PLANNED", "NON_ESTIMABLE"]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_METRICS = ("assignment_rate", "scenario_risk_index")


class PilotCampaignAnalysisError(ValueError):
    """Raised when pilot analysis lineage or frozen coverage is invalid."""


@dataclass(frozen=True, slots=True)
class PilotMetricPlanningOutcome:
    regime_id: str
    metric_id: str
    source_digest: str
    status: PlanningStatus
    estimate: PairedEstimate | None
    power_plan: ProspectivePowerPlan | None
    failure_code: str | None = None
    failure_detail: str | None = None

    def __post_init__(self) -> None:
        if not self.regime_id.strip() or self.metric_id not in _METRICS:
            raise PilotCampaignAnalysisError("pilot metric identity is invalid")
        if not _SHA256.fullmatch(self.source_digest):
            raise PilotCampaignAnalysisError("pilot metric source digest is invalid")
        if self.status == "PLANNED":
            if (
                self.estimate is None
                or self.power_plan is None
                or self.failure_code is not None
                or self.failure_detail is not None
            ):
                raise PilotCampaignAnalysisError("planned pilot metric lineage is incomplete")
        elif self.status == "NON_ESTIMABLE":
            if self.estimate is not None or self.power_plan is not None or not self.failure_code:
                raise PilotCampaignAnalysisError("non-estimable pilot metric lacks failure lineage")
        else:
            raise PilotCampaignAnalysisError("pilot planning status is invalid")

    def payload(self) -> dict[str, object]:
        return {
            "regime_id": self.regime_id,
            "metric_id": self.metric_id,
            "source_digest": self.source_digest,
            "status": self.status,
            "estimate": self.estimate.payload() if self.estimate else None,
            "estimate_digest": self.estimate.report_digest if self.estimate else None,
            "power_plan": self.power_plan.payload() if self.power_plan else None,
            "power_plan_digest": self.power_plan.plan_digest if self.power_plan else None,
            "failure_code": self.failure_code,
            "failure_detail": self.failure_detail,
        }


@dataclass(frozen=True, slots=True)
class PilotCampaignAnalysis:
    protocol_id: str
    protocol_sha256: str
    campaign_plan_digest: str
    pilot_ledger_digest: str
    outcomes: tuple[PilotMetricPlanningOutcome, ...]
    confirmatory_pairs_per_regime: int | None
    disposition: str
    claim_boundary: str = "PILOT_VARIANCE_INPUT_NOT_CONFIRMATORY_EVIDENCE"

    def __post_init__(self) -> None:
        if not self.protocol_id.strip() or any(
            not _SHA256.fullmatch(value)
            for value in (
                self.protocol_sha256,
                self.campaign_plan_digest,
                self.pilot_ledger_digest,
            )
        ):
            raise PilotCampaignAnalysisError("pilot analysis lineage is invalid")
        identities = tuple((item.regime_id, item.metric_id) for item in self.outcomes)
        if len(identities) != 16 or len(set(identities)) != 16:
            raise PilotCampaignAnalysisError("pilot analysis must retain the 16-test family")
        planned = tuple(item for item in self.outcomes if item.status == "PLANNED")
        if len(planned) == 16:
            expected_pairs = max(
                item.power_plan.planned_pair_count
                for item in planned
                if item.power_plan is not None
            )
            if (
                self.confirmatory_pairs_per_regime != expected_pairs
                or self.disposition != "CONFIRMATORY_DESIGN_READY"
            ):
                raise PilotCampaignAnalysisError("ready pilot analysis summary drifted")
        elif (
            self.confirmatory_pairs_per_regime is not None
            or self.disposition != "CONFIRMATORY_BLOCKED_NON_ESTIMABLE_PILOT_RETAINED"
        ):
            raise PilotCampaignAnalysisError("blocked pilot analysis summary drifted")
        if self.claim_boundary != "PILOT_VARIANCE_INPUT_NOT_CONFIRMATORY_EVIDENCE":
            raise PilotCampaignAnalysisError("pilot analysis claim boundary drifted")

    @property
    def analysis_digest(self) -> str:
        return canonical_digest(self.payload())

    @property
    def power_plans(self) -> tuple[ProspectivePowerPlan, ...]:
        return tuple(item.power_plan for item in self.outcomes if item.power_plan is not None)

    def payload(self) -> dict[str, object]:
        return {
            "protocol_id": self.protocol_id,
            "protocol_sha256": self.protocol_sha256,
            "campaign_plan_digest": self.campaign_plan_digest,
            "pilot_ledger_digest": self.pilot_ledger_digest,
            "outcomes": [item.payload() for item in self.outcomes],
            "confirmatory_pairs_per_regime": self.confirmatory_pairs_per_regime,
            "disposition": self.disposition,
            "claim_boundary": self.claim_boundary,
        }


def analyze_pilot_campaign(
    protocol: StatisticalRouteBenchProtocol,
    plan: StatisticalRouteBenchCampaignPlan,
    ledger: StatisticalRouteBenchCampaignLedger,
) -> PilotCampaignAnalysis:
    if (
        plan.phase != "pilot"
        or ledger.phase != "pilot"
        or plan.protocol_id != protocol.protocol_id
        or plan.protocol_sha256 != protocol.manifest_sha256
        or ledger.plan_digest != plan.plan_digest
        or tuple(item.pair_plan for item in ledger.records) != plan.pairs
    ):
        raise PilotCampaignAnalysisError("pilot plan, ledger, or protocol lineage drifted")
    records_by_regime: dict[str, tuple[PairExecutionRecord, ...]] = {
        regime_id: tuple(
            item for item in ledger.records if item.pair_plan.randomness.pair.regime_id == regime_id
        )
        for regime_id in protocol.regime_ids
    }
    if any(
        len(records) != protocol.pilot_replicates_per_regime
        for records in records_by_regime.values()
    ):
        raise PilotCampaignAnalysisError("pilot ledger does not cover every frozen pair")

    outcomes: list[PilotMetricPlanningOutcome] = []
    for regime_id in protocol.regime_ids:
        records = records_by_regime[regime_id]
        for metric_id in _METRICS:
            source_digest = canonical_digest(
                {
                    "pilot_ledger_digest": ledger.ledger_digest,
                    "regime_id": regime_id,
                    "metric_id": metric_id,
                    "record_digests": [item.record_digest for item in records],
                }
            )
            if any(not item.complete for item in records):
                outcomes.append(
                    _non_estimable(
                        regime_id,
                        metric_id,
                        source_digest,
                        "INCOMPLETE_PILOT_PAIR",
                        "At least one frozen pair remains incomplete after its allowed retry.",
                    )
                )
                continue
            observations = tuple(_paired_observation(record, metric_id) for record in records)
            try:
                estimate = estimate_paired(
                    PairedMetricSpec(metric_id, minimum=0.0, maximum=1.0),
                    observations,
                )
                power = plan_primary_power(
                    protocol,
                    PilotVarianceInput(
                        protocol.protocol_id,
                        regime_id,
                        metric_id,
                        len(observations),
                        estimate.standard_deviation**2,
                        "r3_325_pilot",
                        source_digest,
                    ),
                )
            except (PairedEstimationError, ProspectivePowerError) as error:
                outcomes.append(
                    _non_estimable(
                        regime_id,
                        metric_id,
                        source_digest,
                        "NON_ESTIMABLE_PAIRED_VARIANCE_OR_POWER",
                        str(error),
                    )
                )
                continue
            outcomes.append(
                PilotMetricPlanningOutcome(
                    regime_id,
                    metric_id,
                    source_digest,
                    "PLANNED",
                    estimate,
                    power,
                )
            )
    outcome_tuple = tuple(outcomes)
    power_plans = tuple(item.power_plan for item in outcome_tuple if item.power_plan is not None)
    ready = len(power_plans) == 16
    return PilotCampaignAnalysis(
        protocol_id=protocol.protocol_id,
        protocol_sha256=protocol.manifest_sha256,
        campaign_plan_digest=plan.plan_digest,
        pilot_ledger_digest=ledger.ledger_digest,
        outcomes=outcome_tuple,
        confirmatory_pairs_per_regime=(
            max(item.planned_pair_count for item in power_plans) if ready else None
        ),
        disposition=(
            "CONFIRMATORY_DESIGN_READY"
            if ready
            else "CONFIRMATORY_BLOCKED_NON_ESTIMABLE_PILOT_RETAINED"
        ),
    )


def _paired_observation(record: PairExecutionRecord, metric_id: str) -> PairedObservation:
    terminal = {
        role: tuple(item for item in record.attempts if item.arm_role == role)[-1]
        for role in record.pair_plan.arm_order
    }
    candidate = terminal["candidate"]
    comparator = terminal["comparator"]
    return PairedObservation(
        record.pair_plan.randomness,
        _metric_value(candidate, metric_id),
        _metric_value(comparator, metric_id),
    )


def _metric_value(attempt: ArmExecutionAttempt, metric_id: str) -> float:
    value = (
        attempt.assignment_rate if metric_id == "assignment_rate" else attempt.scenario_risk_index
    )
    if value is None:
        raise PilotCampaignAnalysisError("complete pilot attempt lacks a primary metric")
    return value


def _non_estimable(
    regime_id: str,
    metric_id: str,
    source_digest: str,
    failure_code: str,
    failure_detail: str,
) -> PilotMetricPlanningOutcome:
    return PilotMetricPlanningOutcome(
        regime_id,
        metric_id,
        source_digest,
        "NON_ESTIMABLE",
        None,
        None,
        failure_code,
        failure_detail[:240],
    )


__all__ = [
    "PilotCampaignAnalysis",
    "PilotCampaignAnalysisError",
    "PilotMetricPlanningOutcome",
    "PlanningStatus",
    "analyze_pilot_campaign",
]
