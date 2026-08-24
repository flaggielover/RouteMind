from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from routemind_compute.application import statistical_routebench_analysis as analysis_module
from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_analysis import (
    PilotCampaignAnalysisError,
    PilotMetricPlanningOutcome,
    analyze_pilot_campaign,
)
from routemind_compute.application.statistical_routebench_campaign import (
    ArmExecutionAttempt,
    ArmOutcome,
    ArmRole,
    CampaignAuthorization,
    PilotPairExecutionPlan,
    StatisticalRouteBenchCampaignLedger,
    StatisticalRouteBenchCampaignPlan,
    build_confirmatory_campaign_plan,
    build_pilot_campaign_plan,
    execute_campaign,
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
    load_statistical_routebench_protocol,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "statistical-routebench"
    / "statistical-routebench-v1.json"
)
STREAMS = tuple(
    (name, canonical_digest(name)) for name in ("demand", "merchant", "courier", "traffic")
)


def protocol() -> StatisticalRouteBenchProtocol:
    return replace(
        load_statistical_routebench_protocol(PROTOCOL_PATH),
        protocol_id="synthetic-pilot-analysis",
    )


def campaign() -> StatisticalRouteBenchCampaignPlan:
    return build_pilot_campaign_plan(
        protocol(),
        "synthetic-analysis-pilot",
        CampaignAuthorization("1" * 40, 123456, "success", "2026-08-24T12:00:00Z"),
    )


def variable_attempt(
    pair: PilotPairExecutionPlan,
    role: ArmRole,
    number: int,
    outcome: ArmOutcome = "COMPLETED",
) -> ArmExecutionAttempt:
    replicate = pair.randomness.pair.replicate
    candidate = role == "candidate"
    defect = outcome in {"HARNESS_DEFECT", "INFRASTRUCTURE_DEFECT"}
    assigned = (80 + replicate) if candidate else 75
    risk = (0.40 + replicate / 100) if candidate else 0.60
    strategy = pair.candidate_strategy if candidate else pair.comparator_strategy
    return ArmExecutionAttempt(
        pair_plan_digest=pair.pair_plan_digest,
        arm_role=role,
        strategy=strategy,
        strategy_version="1.0.0",
        attempt=number,
        outcome=outcome,
        started_at_utc="2026-08-24T12:00:00.000Z",
        completed_at_utc="2026-08-24T12:00:00.001Z",
        request_count=None if defect else 100,
        assigned_count=None if defect else assigned,
        scenario_risk_index=None if defect else risk,
        assignment_rate=None if defect else assigned / 100,
        runtime_millis=1.0,
        strategy_failure_count=0,
        fallback_count=0,
        timeout_count=0,
        event_ids=() if defect else tuple(f"event-{index}" for index in range(100)),
        scenario_manifest_digest=None if defect else "a" * 64,
        stream_realization_digests=() if defect else STREAMS,
        deterministic_result_digest=canonical_digest(
            [pair.pair_plan_digest, role, number, outcome]
        ),
        failure_code="SYNTHETIC_DEFECT" if defect else None,
    )


def constant_attempt(
    pair: PilotPairExecutionPlan, role: ArmRole, number: int
) -> ArmExecutionAttempt:
    return replace(
        variable_attempt(pair, role, number),
        assigned_count=80,
        assignment_rate=0.8,
        scenario_risk_index=0.5,
    )


def test_pilot_analysis_generates_all_16_observed_power_plans() -> None:
    frozen = protocol()
    plan = campaign()
    ledger = execute_campaign(plan, variable_attempt)

    analysis = analyze_pilot_campaign(frozen, plan, ledger)

    assert analysis.disposition == "CONFIRMATORY_DESIGN_READY"
    assert analysis.confirmatory_pairs_per_regime is not None
    assert len(analysis.outcomes) == 16
    assert len(analysis.power_plans) == 16
    assert all(item.status == "PLANNED" for item in analysis.outcomes)
    assert all(item.power_plan and item.power_plan.observed_pilot for item in analysis.outcomes)
    assert all(item.estimate and item.estimate.n == 8 for item in analysis.outcomes)
    assert analysis.analysis_digest == canonical_digest(analysis.payload())

    confirmatory = build_confirmatory_campaign_plan(
        frozen,
        "synthetic-analysis-confirmatory",
        plan.authorization,
        ledger.ledger_digest,
        analysis.power_plans,
    )
    assert confirmatory.resource_estimate.pairs_per_regime == analysis.confirmatory_pairs_per_regime


def test_zero_variance_is_retained_as_non_estimable_without_fabricated_power() -> None:
    frozen = protocol()
    plan = campaign()
    ledger = execute_campaign(plan, constant_attempt)

    analysis = analyze_pilot_campaign(frozen, plan, ledger)

    assert analysis.disposition == "CONFIRMATORY_BLOCKED_NON_ESTIMABLE_PILOT_RETAINED"
    assert analysis.confirmatory_pairs_per_regime is None
    assert not analysis.power_plans
    assert len(analysis.outcomes) == 16
    assert all(item.status == "NON_ESTIMABLE" for item in analysis.outcomes)
    assert all(
        item.failure_code == "NON_ESTIMABLE_PAIRED_VARIANCE_OR_POWER" for item in analysis.outcomes
    )
    assert all("zero variance" in (item.failure_detail or "") for item in analysis.outcomes)


def test_incomplete_pair_blocks_only_affected_regime_metrics_and_remains_visible() -> None:
    frozen = protocol()
    plan = campaign()
    first = plan.pairs[0]

    def persistent_defect(
        pair: PilotPairExecutionPlan, role: ArmRole, number: int
    ) -> ArmExecutionAttempt:
        if pair == first and role == first.arm_order[0]:
            return variable_attempt(pair, role, number, "HARNESS_DEFECT")
        return variable_attempt(pair, role, number)

    ledger = execute_campaign(plan, persistent_defect)
    analysis = analyze_pilot_campaign(frozen, plan, ledger)

    blocked = tuple(
        item for item in analysis.outcomes if item.failure_code == "INCOMPLETE_PILOT_PAIR"
    )
    assert len(blocked) == 2
    assert {item.metric_id for item in blocked} == {
        "assignment_rate",
        "scenario_risk_index",
    }
    assert all(item.regime_id == "normal" for item in blocked)
    assert len(analysis.power_plans) == 14
    assert analysis.confirmatory_pairs_per_regime is None


@pytest.mark.parametrize(
    "change",
    (
        "ledger_phase",
        "protocol_id",
        "manifest",
        "ledger_digest",
        "record_order",
    ),
)
def test_pilot_analysis_rejects_plan_ledger_and_protocol_lineage_drift(change: str) -> None:
    frozen = protocol()
    plan = campaign()
    ledger = execute_campaign(plan, variable_attempt)
    if change == "ledger_phase":
        ledger = replace(
            ledger,
            phase="confirmatory",
            disposition="CONFIRMATORY_COMPLETE_FOR_FROZEN_ANALYSIS",
            claim_boundary="CONFIRMATORY_EVIDENCE_REQUIRES_FROZEN_STATISTICAL_GATES",
        )
    elif change == "protocol_id":
        frozen = replace(frozen, protocol_id="other")
    elif change == "manifest":
        frozen = replace(frozen, manifest_sha256="b" * 64)
    elif change == "ledger_digest":
        ledger = replace(ledger, plan_digest="b" * 64)
    else:
        ledger = replace(ledger, records=tuple(reversed(ledger.records)))
    with pytest.raises(PilotCampaignAnalysisError, match="lineage drifted"):
        analyze_pilot_campaign(frozen, plan, ledger)


def test_pilot_analysis_value_objects_reject_forged_status_and_summary() -> None:
    source = "a" * 64
    with pytest.raises(PilotCampaignAnalysisError, match="metric identity"):
        PilotMetricPlanningOutcome("", "assignment_rate", source, "NON_ESTIMABLE", None, None, "x")
    with pytest.raises(PilotCampaignAnalysisError, match="source digest"):
        PilotMetricPlanningOutcome(
            "normal", "assignment_rate", "short", "NON_ESTIMABLE", None, None, "x"
        )
    with pytest.raises(PilotCampaignAnalysisError, match="failure lineage"):
        PilotMetricPlanningOutcome("normal", "assignment_rate", source, "NON_ESTIMABLE", None, None)

    ready_plan = campaign()
    ready_ledger = execute_campaign(ready_plan, variable_attempt)
    ready = analyze_pilot_campaign(protocol(), ready_plan, ready_ledger)
    with pytest.raises(PilotCampaignAnalysisError, match=r"planned.*incomplete"):
        replace(ready.outcomes[0], estimate=None)
    with pytest.raises(PilotCampaignAnalysisError, match="status is invalid"):
        replace(ready.outcomes[0], status="OTHER")  # type: ignore[arg-type]
    with pytest.raises(PilotCampaignAnalysisError, match="analysis lineage"):
        replace(ready, protocol_sha256="short")
    with pytest.raises(PilotCampaignAnalysisError, match=r"ready.*summary"):
        replace(ready, confirmatory_pairs_per_regime=1)

    plan = campaign()
    ledger: StatisticalRouteBenchCampaignLedger = execute_campaign(plan, constant_attempt)
    analysis = analyze_pilot_campaign(protocol(), plan, ledger)
    with pytest.raises(PilotCampaignAnalysisError, match="16-test family"):
        replace(analysis, outcomes=analysis.outcomes[:-1])
    with pytest.raises(PilotCampaignAnalysisError, match=r"blocked.*summary"):
        replace(analysis, confirmatory_pairs_per_regime=20)
    with pytest.raises(PilotCampaignAnalysisError, match="claim boundary"):
        replace(analysis, claim_boundary="other")


def test_analysis_rejects_missing_regime_and_metric_on_defect_attempt() -> None:
    frozen = protocol()
    plan = campaign()
    ledger = execute_campaign(plan, variable_attempt)
    with pytest.raises(PilotCampaignAnalysisError, match="cover every frozen pair"):
        analyze_pilot_campaign(
            replace(frozen, regime_ids=(*frozen.regime_ids, "missing-regime")),
            plan,
            ledger,
        )
    defect = variable_attempt(plan.pairs[0], "candidate", 1, "HARNESS_DEFECT")
    with pytest.raises(PilotCampaignAnalysisError, match="lacks a primary metric"):
        analysis_module._metric_value(defect, "assignment_rate")
