from __future__ import annotations

import pytest

from routemind_compute.application.r4_decision_logging import (
    DecisionLoggingPolicy,
    DecisionLogRecord,
    DecisionLogStore,
)


def record(**overrides: object) -> DecisionLogRecord:
    values: dict[str, object] = {
        "decision_id": "decision-1",
        "tenant_key": "rtk_unattributed",
        "policy_id": "policy",
        "policy_version": "1.0.0",
        "action_set": ("nearest", "weighted-greedy"),
        "selected_action": "nearest",
        "action_mode": "DETERMINISTIC",
        "propensity": None,
        "state_digest": "a" * 64,
        "shared_resource_digest": "b" * 64,
        "outcome_digest": "c" * 64,
        "decision_sequence": 0,
    }
    values.update(overrides)
    return DecisionLogRecord.create(**values)  # type: ignore[arg-type]


def test_empty_and_deterministic_logs_remain_non_identifiable() -> None:
    empty = DecisionLogStore().audit_support()
    assert empty.status == "INSUFFICIENT_DATA"
    store = DecisionLogStore()
    store.append(record())
    report = store.audit_support()
    assert report.status == "OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS"
    assert report.deterministic_count == 1


def test_stochastic_overlap_is_measured_without_promoting_a_causal_claim() -> None:
    store = DecisionLogStore()
    store.append(record(decision_id="decision-1", action_mode="STOCHASTIC", propensity=0.5))
    store.append(
        record(
            decision_id="decision-2",
            selected_action="weighted-greedy",
            action_mode="STOCHASTIC",
            propensity=0.5,
            decision_sequence=1,
        )
    )
    report = store.audit_support()
    assert report.status == "SUPPORT_DIAGNOSTIC_POSITIVE_NOT_CAUSAL"
    assert report.overlap_ratio == 1.0
    assert report.action_counts == (("nearest", 1), ("weighted-greedy", 1))


def test_retroactive_duplicate_limit_and_contract_tampering_are_rejected() -> None:
    store = DecisionLogStore(DecisionLoggingPolicy(max_records=1))
    value = record()
    with pytest.raises(ValueError, match="retroactive"):
        store.append(value, captured_at_decision=False)
    store.append(value)
    with pytest.raises(ValueError, match="duplicate"):
        store.append(value)
    with pytest.raises(ValueError, match="retention"):
        store.append(record(decision_id="decision-2", decision_sequence=1))
    with pytest.raises(ValueError, match="fabricated"):
        record(action_mode="DETERMINISTIC", propensity=1.0)
    with pytest.raises(ValueError, match="record_digest"):
        DecisionLogRecord(
            value.decision_id,
            value.tenant_key,
            value.policy_id,
            value.policy_version,
            value.action_set,
            value.selected_action,
            value.action_mode,
            value.propensity,
            value.state_digest,
            value.shared_resource_digest,
            value.outcome_digest,
            value.decision_sequence,
            "d" * 64,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("decision_id", "", "decision_id"),
        ("tenant_key", "raw-tenant", "pseudonymized"),
        ("state_digest", "bad", "state_digest"),
        ("action_set", (), "action_set"),
        ("action_set", ("nearest", "nearest"), "action_set"),
        ("action_set", ("nearest", "unsafe value"), "action_set"),
        ("selected_action", "other", "selected_action"),
        ("action_mode", "UNKNOWN", "action_mode"),
        ("decision_sequence", -1, "decision_sequence"),
    ],
)
def test_decision_record_boundaries_fail_closed(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        record(**{field: value})


@pytest.mark.parametrize("propensity", [None, 0.0, -0.1, 1.1, float("inf")])
def test_stochastic_propensity_requires_exact_finite_probability(propensity: float | None) -> None:
    with pytest.raises(ValueError, match="propensity"):
        record(action_mode="STOCHASTIC", propensity=propensity)


def test_overlap_gap_and_serialization_are_explicit() -> None:
    store = DecisionLogStore()
    store.append(record(action_mode="STOCHASTIC", propensity=0.5))
    store.append(
        record(
            decision_id="decision-2",
            action_set=("other",),
            selected_action="other",
            action_mode="STOCHASTIC",
            propensity=0.5,
            decision_sequence=1,
        )
    )
    report = store.audit_support()
    assert report.status == "OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS"
    assert report.as_dict()["claim_boundary"] == "support_diagnostic_only"
    with pytest.raises(ValueError, match="positive"):
        DecisionLoggingPolicy(max_records=0)
    assert store.records
