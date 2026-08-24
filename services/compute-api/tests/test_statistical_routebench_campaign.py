from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_campaign import (
    ArmExecutionAttempt,
    ArmOutcome,
    ArmRole,
    CampaignAuthorization,
    PairExecutionRecord,
    PilotPairExecutionPlan,
    StatisticalRouteBenchCampaignError,
    StatisticalRouteBenchCampaignLedger,
    build_confirmatory_campaign_plan,
    build_pilot_campaign_plan,
    execute_campaign,
    execute_campaign_pair,
    execute_pilot_campaign,
    summarize_campaign_records,
)
from routemind_compute.application.statistical_routebench_power import (
    PilotVarianceInput,
    ProspectivePowerPlan,
    plan_primary_power,
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
    load_statistical_routebench_protocol,
)
from routemind_compute.application.statistical_routebench_randomness import (
    PairIdentity,
    build_common_random_number_plan,
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
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
STREAMS = tuple(
    (name, canonical_digest(name)) for name in ("demand", "merchant", "courier", "traffic")
)


def protocol() -> StatisticalRouteBenchProtocol:
    return load_statistical_routebench_protocol(PROTOCOL_PATH)


def authorization() -> CampaignAuthorization:
    return CampaignAuthorization("1" * 40, 123456, "success", "2026-08-24T12:00:00Z")


def observed_power_plans() -> tuple[ProspectivePowerPlan, ...]:
    frozen = protocol()
    return tuple(
        plan_primary_power(
            frozen,
            PilotVarianceInput(
                frozen.protocol_id,
                regime_id,
                metric_id,
                8,
                0.0001 + index * 0.000001,
                "r3_325_pilot",
                canonical_digest([regime_id, metric_id]),
            ),
        )
        for index, (regime_id, metric_id) in enumerate(
            (regime_id, metric_id)
            for regime_id in frozen.regime_ids
            for metric_id in ("assignment_rate", "scenario_risk_index")
        )
    )


def attempt(
    pair: PilotPairExecutionPlan,
    role: ArmRole,
    number: int = 1,
    outcome: ArmOutcome = "COMPLETED",
) -> ArmExecutionAttempt:
    pair_plan = pair
    strategy = (
        pair_plan.candidate_strategy if role == "candidate" else pair_plan.comparator_strategy
    )
    defect = outcome in {"HARNESS_DEFECT", "INFRASTRUCTURE_DEFECT"}
    scored_failure = outcome in {"TIMEOUT", "STRATEGY_FAILURE"}
    request_count = None if defect else 2
    assigned_count = None if defect else (0 if scored_failure else 1)
    risk = None if defect else (1.0 if scored_failure else 0.5)
    rate = None if defect else (0.0 if scored_failure else 0.5)
    return ArmExecutionAttempt(
        pair_plan_digest=pair_plan.pair_plan_digest,
        arm_role=role,
        strategy=strategy,
        strategy_version="1.0.0",
        attempt=number,
        outcome=outcome,
        started_at_utc="2026-08-24T12:00:00.000Z",
        completed_at_utc="2026-08-24T12:00:00.001Z",
        request_count=request_count,
        assigned_count=assigned_count,
        scenario_risk_index=risk,
        assignment_rate=rate,
        runtime_millis=1.0,
        strategy_failure_count=2 if outcome == "STRATEGY_FAILURE" else 0,
        fallback_count=1 if outcome == "FALLBACK" else 0,
        timeout_count=2 if outcome == "TIMEOUT" else 0,
        event_ids=() if defect else ("event-1", "event-2"),
        scenario_manifest_digest=None if defect else SHA_B,
        stream_realization_digests=() if defect else STREAMS,
        deterministic_result_digest=SHA_C,
        failure_code="EXPECTED_TEST_FAILURE" if defect or scored_failure else None,
    )


def test_pilot_plan_freezes_matrix_resources_randomness_and_order() -> None:
    plan = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization())

    assert len(plan.pairs) == 64
    assert plan.resource_estimate.arm_runs == 128
    assert plan.resource_estimate.maximum_arm_wall_seconds == 3840
    assert plan.resource_estimate.expected_peak_memory_mebibytes == 1024
    assert plan.resource_estimate.maximum_external_artifact_mebibytes == 512
    assert plan.resource_estimate.external_cost_usd == 0.0
    assert plan.phase == "pilot"
    assert not plan.material_results_present
    counts = Counter(item.randomness.pair.regime_id for item in plan.pairs)
    assert counts == Counter({regime_id: 8 for regime_id in protocol().regime_ids})
    assert plan.pairs[0].arm_order == ("candidate", "comparator")
    assert plan.pairs[1].arm_order == ("comparator", "candidate")
    assert plan.pairs[0].randomness.pair.replicate == 0
    assert plan.pairs[-1].randomness.pair.replicate == 7
    assert plan.pairs[0].candidate_parameter_digest != plan.pairs[0].comparator_parameter_digest
    assert plan.plan_digest == canonical_digest(plan.payload())
    assert plan.authorization.authorization_digest == canonical_digest(plan.authorization.payload())


def test_confirmatory_plan_binds_all_observed_power_plans_before_execution() -> None:
    frozen = protocol()
    plans = observed_power_plans()

    campaign = build_confirmatory_campaign_plan(
        frozen,
        "r3-325-confirmatory-test",
        authorization(),
        SHA_A,
        plans,
    )

    expected_pairs = max(item.planned_pair_count for item in plans)
    assert campaign.phase == "confirmatory"
    assert campaign.resource_estimate.pairs_per_regime == expected_pairs
    assert campaign.resource_estimate.arm_runs == expected_pairs * 8 * 2
    assert campaign.resource_estimate.arm_runs <= 3200
    assert campaign.pairs[0].randomness.pair.replicate == 1000
    assert campaign.pairs[-1].randomness.pair.replicate == 999 + expected_pairs
    assert campaign.pilot_ledger_digest == SHA_A
    assert campaign.power_plan_digests == tuple(sorted(item.plan_digest for item in plans))
    pilot = build_pilot_campaign_plan(frozen, "r3-325-pilot-other", authorization())
    assert {
        stream.seed for pair in campaign.pairs for stream in pair.randomness.streams
    }.isdisjoint({stream.seed for pair in pilot.pairs for stream in pair.randomness.streams})


def test_confirmatory_plan_rejects_missing_or_synthetic_power_lineage() -> None:
    frozen = protocol()
    synthetic = tuple(
        plan_primary_power(
            frozen,
            PilotVarianceInput(
                frozen.protocol_id,
                regime_id,
                metric_id,
                8,
                0.0001,
                "synthetic_validation",
                canonical_digest([regime_id, metric_id]),
            ),
        )
        for regime_id in frozen.regime_ids
        for metric_id in ("assignment_rate", "scenario_risk_index")
    )
    with pytest.raises(StatisticalRouteBenchCampaignError, match="identity drifted"):
        build_confirmatory_campaign_plan(
            frozen, "r3-325-confirmatory-test", authorization(), SHA_A, synthetic
        )
    with pytest.raises(StatisticalRouteBenchCampaignError, match="16-test family"):
        build_confirmatory_campaign_plan(
            frozen, "r3-325-confirmatory-test", authorization(), SHA_A, synthetic[:-1]
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"implementation_revision": "short"}, "full lowercase"),
        ({"implementation_ci_run": 0}, "must be positive"),
        ({"implementation_ci_run": True}, "must be positive"),
        ({"implementation_ci_conclusion": "failure"}, "successful"),
        ({"authorized_at_utc": "2026-08-24"}, "RFC 3339"),
        ({"scope": "other"}, "scope"),
    ),
)
def test_authorization_rejects_unverified_material_execution(
    changes: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "implementation_revision": "1" * 40,
        "implementation_ci_run": 123456,
        "implementation_ci_conclusion": "success",
        "authorized_at_utc": "2026-08-24T12:00:00Z",
        "scope": "r3_325_material_execution",
    }
    values.update(changes)
    with pytest.raises(StatisticalRouteBenchCampaignError, match=message):
        CampaignAuthorization(**values)  # type: ignore[arg-type]


def test_plan_rejects_protocol_coverage_and_resource_drift() -> None:
    frozen = protocol()
    plan = build_pilot_campaign_plan(frozen, "r3-325-pilot-test", authorization())
    other = replace(frozen, protocol_id="synthetic-validation")
    drifted_randomness = build_common_random_number_plan(other, "pilot", "normal", 0)
    drifted_pair = replace(plan.pairs[0], randomness=drifted_randomness)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="protocol"):
        replace(plan, pairs=(drifted_pair, *plan.pairs[1:]))
    with pytest.raises(StatisticalRouteBenchCampaignError, match="resource arithmetic"):
        replace(plan.resource_estimate, arm_runs=126)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="resource dimensions"):
        replace(plan.resource_estimate, pair_count=True)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="resource envelope"):
        replace(plan.resource_estimate, external_cost_usd=True)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="artifact root"):
        replace(plan, artifact_relative_root="elsewhere")


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"campaign_id": "short"}, "campaign id"),
        ({"protocol_id": ""}, "protocol identity"),
        ({"protocol_sha256": "short"}, "protocol identity"),
        ({"material_results_present": True}, "phase or result"),
        ({"generator_version": "other"}, "generator boundary"),
        ({"power_plan_digests": (SHA_A,)}, "pilot plan claim"),
        ({"pairs": ()}, "pair count"),
    ),
)
def test_campaign_plan_rejects_identity_and_claim_drift(
    changes: dict[str, object], message: str
) -> None:
    campaign = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization())
    with pytest.raises(StatisticalRouteBenchCampaignError, match=message):
        replace(campaign, **changes)  # type: ignore[arg-type]


def test_pair_plan_and_campaign_coverage_validation_reject_drift() -> None:
    campaign = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization())
    pair = campaign.pairs[0]
    with pytest.raises(StatisticalRouteBenchCampaignError, match="parity"):
        replace(pair, arm_order=("comparator", "candidate"))
    with pytest.raises(StatisticalRouteBenchCampaignError, match="must not be blank"):
        replace(pair, candidate_strategy="")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="distinct"):
        replace(pair, candidate_strategy=pair.comparator_strategy)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="SHA-256"):
        replace(pair, candidate_parameter_digest="short")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="duplicate pairs"):
        replace(campaign, pairs=(campaign.pairs[0], campaign.pairs[0], *campaign.pairs[2:]))

    identity = PairIdentity(
        pair.randomness.pair.protocol_id,
        "pilot",
        pair.randomness.pair.regime_id,
        8,
    )
    streams = tuple(replace(item, pair=identity) for item in pair.randomness.streams)
    out_of_range = replace(pair.randomness, pair=identity, streams=streams)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="replicate coverage"):
        replace(campaign, pairs=(replace(pair, randomness=out_of_range), *campaign.pairs[1:]))


def test_campaign_executes_every_seed_and_retains_successes() -> None:
    plan = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization())
    ledger = execute_pilot_campaign(plan, attempt)

    assert len(ledger.records) == 64
    assert ledger.retained_attempt_count == 128
    assert ledger.complete_pair_count == 64
    assert ledger.outcome_counts == (("COMPLETED", 128),)
    assert ledger.disposition == "PILOT_COMPLETE_FOR_VARIANCE_ONLY"
    assert tuple(item.pair_plan for item in ledger.records) == plan.pairs
    assert ledger.ledger_digest == canonical_digest(ledger.payload())


def test_campaign_retries_defect_once_and_retains_both_attempts() -> None:
    plan = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization())
    first_pair = plan.pairs[0]

    def flaky(pair: PilotPairExecutionPlan, role: ArmRole, number: int) -> ArmExecutionAttempt:
        outcome: ArmOutcome = (
            "HARNESS_DEFECT"
            if pair == first_pair and role == first_pair.arm_order[0] and number == 1
            else "COMPLETED"
        )
        return attempt(pair, role, number, outcome)

    ledger = execute_campaign(plan, flaky)

    assert ledger.retained_attempt_count == 129
    assert ledger.complete_pair_count == 64
    assert ledger.outcome_counts == (("COMPLETED", 128), ("HARNESS_DEFECT", 1))
    assert tuple(item.attempt for item in ledger.records[0].attempts[:2]) == (1, 2)


def test_campaign_retains_persistent_defect_and_fails_completion() -> None:
    plan = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization())
    first_pair = plan.pairs[0]

    def broken(pair: PilotPairExecutionPlan, role: ArmRole, number: int) -> ArmExecutionAttempt:
        outcome: ArmOutcome = (
            "INFRASTRUCTURE_DEFECT"
            if pair == first_pair and role == first_pair.arm_order[0]
            else "COMPLETED"
        )
        return attempt(pair, role, number, outcome)

    ledger = execute_campaign(plan, broken)

    assert ledger.retained_attempt_count == 129
    assert ledger.complete_pair_count == 63
    assert ledger.disposition == "PILOT_INCOMPLETE_RETAIN_ALL_OUTPUTS"
    assert not ledger.records[0].complete


def test_confirmatory_campaign_executes_with_confirmatory_disposition() -> None:
    campaign = build_confirmatory_campaign_plan(
        protocol(),
        "r3-325-confirmatory-test",
        authorization(),
        SHA_A,
        observed_power_plans(),
    )
    ledger = execute_campaign(campaign, attempt)

    assert ledger.phase == "confirmatory"
    assert ledger.complete_pair_count == len(campaign.pairs)
    assert ledger.disposition == "CONFIRMATORY_COMPLETE_FOR_FROZEN_ANALYSIS"
    with pytest.raises(StatisticalRouteBenchCampaignError, match="requires a pilot plan"):
        execute_pilot_campaign(campaign, attempt)


def test_executor_and_record_validation_fail_closed_on_identity_or_order_drift() -> None:
    plan = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization())
    pair = plan.pairs[0]

    def drifted(
        pair_value: PilotPairExecutionPlan, role: ArmRole, number: int
    ) -> ArmExecutionAttempt:
        return replace(attempt(pair_value, role, number), strategy="nearest")

    with pytest.raises(StatisticalRouteBenchCampaignError, match="drifted arm identity"):
        execute_campaign_pair(pair, drifted)
    candidate = attempt(pair, "candidate")
    comparator = attempt(pair, "comparator")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="execution order"):
        PairExecutionRecord(pair, (comparator, candidate))
    with pytest.raises(StatisticalRouteBenchCampaignError, match="only a retained defect"):
        PairExecutionRecord(
            pair,
            (candidate, replace(candidate, attempt=2), comparator),
        )
    with pytest.raises(StatisticalRouteBenchCampaignError, match="share realized randomness"):
        PairExecutionRecord(
            pair,
            (candidate, replace(comparator, scenario_manifest_digest=SHA_A)),
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"runtime_millis": float("inf")}, "runtime or role"),
        ({"completed_at_utc": "2026-08-24T11:59:59Z"}, "ordered UTC"),
        ({"assignment_rate": 0.25}, "does not match"),
        ({"scenario_manifest_digest": "short"}, "scenario manifest"),
        ({"stream_realization_digests": STREAMS[:-1]}, "stream realization"),
        ({"failure_code": "unexpected"}, "completed arms"),
    ),
)
def test_arm_attempt_rejects_invalid_metrics_lineage_and_time(
    changes: dict[str, object], message: str
) -> None:
    pair = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization()).pairs[0]
    with pytest.raises(StatisticalRouteBenchCampaignError, match=message):
        replace(attempt(pair, "candidate"), **changes)  # type: ignore[arg-type]


def test_defect_and_scored_failure_validation_forbids_fabricated_results() -> None:
    pair = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization()).pairs[0]
    defect = attempt(pair, "candidate", outcome="HARNESS_DEFECT")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="fabricate metrics"):
        replace(defect, request_count=2)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="scenario lineage"):
        replace(defect, scenario_manifest_digest=SHA_A)
    timeout = attempt(pair, "candidate", outcome="TIMEOUT")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="worst-case"):
        replace(timeout, assigned_count=1, assignment_rate=0.5)
    fallback = attempt(pair, "candidate", outcome="FALLBACK")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="fallback count"):
        replace(fallback, fallback_count=0)


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"pair_plan_digest": "short"}, "digests"),
        ({"strategy": ""}, "strategy identity"),
        ({"strategy_version": "2.0.0"}, "strategy identity"),
        ({"attempt": 3}, "attempt"),
        ({"started_at_utc": "not-a-time"}, "RFC 3339"),
        ({"started_at_utc": "2026-99-99T12:00:00Z"}, "timestamps are invalid"),
        ({"runtime_millis": -1.0}, "runtime must"),
        ({"strategy_failure_count": -1}, "diagnostic counts"),
        ({"request_count": None}, "metrics or event"),
        ({"event_ids": ("event-1", "event-1")}, "metrics or event"),
        ({"outcome": "UNKNOWN"}, "outcome is invalid"),
    ),
)
def test_arm_attempt_rejects_additional_structural_drift(
    changes: dict[str, object], message: str
) -> None:
    pair = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization()).pairs[0]
    with pytest.raises(StatisticalRouteBenchCampaignError, match=message):
        replace(attempt(pair, "candidate"), **changes)  # type: ignore[arg-type]


def test_pair_record_rejects_missing_wrong_or_misnumbered_attempts() -> None:
    pair = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization()).pairs[0]
    candidate = attempt(pair, "candidate")
    comparator = attempt(pair, "comparator")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="retain attempts"):
        PairExecutionRecord(pair, ())
    with pytest.raises(StatisticalRouteBenchCampaignError, match="escaped its pair"):
        PairExecutionRecord(pair, (replace(candidate, pair_plan_digest=SHA_A), comparator))
    with pytest.raises(StatisticalRouteBenchCampaignError, match="one or two attempts"):
        PairExecutionRecord(pair, (candidate,))
    defect = attempt(pair, "candidate", outcome="HARNESS_DEFECT")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="attempt sequence"):
        PairExecutionRecord(pair, (replace(defect, attempt=2), comparator))
    with pytest.raises(StatisticalRouteBenchCampaignError, match="frozen role"):
        PairExecutionRecord(pair, (replace(candidate, strategy="nearest"), comparator))


def test_summary_and_ledger_reject_partial_or_forged_aggregates() -> None:
    plan = build_pilot_campaign_plan(protocol(), "r3-325-pilot-test", authorization())
    record = execute_campaign_pair(plan.pairs[0], attempt)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="cover the plan"):
        summarize_campaign_records(plan, (record,))
    ledger = execute_campaign(plan, attempt)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="summary"):
        replace(ledger, retained_attempt_count=127)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="duplicate"):
        StatisticalRouteBenchCampaignLedger(
            plan.plan_digest,
            (record, record),
            4,
            2,
            (("COMPLETED", 4),),
            "PILOT_COMPLETE_FOR_VARIANCE_ONLY",
        )
    with pytest.raises(StatisticalRouteBenchCampaignError, match="plan digest"):
        replace(ledger, plan_digest="short")
    with pytest.raises(StatisticalRouteBenchCampaignError, match="phase"):
        replace(ledger, phase="other")


def test_builders_reject_mutated_resource_envelopes() -> None:
    frozen = protocol()
    pilot_resource = replace(frozen.resource_envelope, pilot_arm_runs=126)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="pilot arm count"):
        build_pilot_campaign_plan(
            replace(frozen, resource_envelope=pilot_resource),
            "r3-325-pilot-test",
            authorization(),
        )
    confirmatory_resource = replace(frozen.resource_envelope, maximum_confirmatory_arm_runs=1)
    with pytest.raises(StatisticalRouteBenchCampaignError, match="arm-run envelope"):
        build_confirmatory_campaign_plan(
            replace(frozen, resource_envelope=confirmatory_resource),
            "r3-325-confirmatory-test",
            authorization(),
            SHA_A,
            observed_power_plans(),
        )
