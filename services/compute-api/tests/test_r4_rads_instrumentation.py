from __future__ import annotations

from typing import Any, cast

import pytest

from routemind_compute.application.r4_rads_instrumentation import (
    RadsInstrumentationRecorder,
    RadsTick,
)


def tick(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "run_id": "r4-434-fixture",
        "manifest_digest": "a" * 64,
        "request_id": "request-1",
        "tick": 0,
        "variant": "rads-h@1.0.0",
        "policy_version": "policy@1.0.0",
        "state_digest": "b" * 64,
        "action_id": "weighted-greedy",
        "action_set": ("nearest", "weighted-greedy"),
        "previous_policy": "nearest",
        "selected_policy": "weighted-greedy",
        "switch_occurred": True,
        "constraint_status": "SATISFIED",
        "fallback_state": "NONE",
        "latency_ms": 2.5,
        "outcome_status": "COMPLETED",
        "outcome_digest": "c" * 64,
        "lineage_digest": "d" * 64,
        "tenant_key": "rtk_unattributed",
    }
    values.update(overrides)
    return values


def test_tick_record_metrics_and_replay_digest_are_deterministic() -> None:
    recorder = RadsInstrumentationRecorder()
    recorder.record(**tick())
    recorder.record(
        **tick(
            tick=1,
            action_id="nearest",
            previous_policy="weighted-greedy",
            selected_policy="nearest",
            switch_occurred=True,
            variant="safe-rads@1.0.0",
            fallback_state="TRAVEL_FALLBACK",
        )
    )
    metrics = recorder.metrics()
    assert metrics["tick_count"] == 2
    assert metrics["switch_count"] == 2
    assert metrics["fallback_count"] == 1
    assert metrics["variant_counts"] == (("rads-h@1.0.0", 1), ("safe-rads@1.0.0", 1))
    assert recorder.replay_digest() == recorder.replay_digest()


def test_missing_fields_are_retained_as_explicit_failure() -> None:
    recorder = RadsInstrumentationRecorder()
    with pytest.raises(ValueError, match="required instrumentation fields missing"):
        recorder.record(run_id="run-1", tick=2, action_id="nearest")
    assert recorder.failures[0].missing_fields == (
        "manifest_digest",
        "request_id",
        "variant",
        "state_digest",
        "action_set",
        "constraint_status",
        "fallback_state",
        "latency_ms",
        "outcome_status",
        "outcome_digest",
        "lineage_digest",
    )
    failure = recorder.record_failure(
        run_id="run-1", tick=3, reason="provider_unavailable", missing_fields=("travel_time",)
    )
    assert failure.status == "FAILED"
    assert recorder.metrics()["failure_count"] == 2


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("action_id", "not-in-set", "action_id"),
        ("switch_occurred", False, "switch_occurred"),
        ("state_digest", "not-a-digest", "state_digest"),
        ("latency_ms", -1.0, "latency_ms"),
    ],
)
def test_tick_contract_rejects_invalid_fields(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        RadsTick(**cast(dict[str, Any], tick(**{field: value})))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("run_id", "", "run_id"),
        ("manifest_digest", "bad", "manifest_digest"),
        ("tick", -1, "tick"),
        ("action_set", (), "action_set"),
        ("action_set", ("nearest", "nearest"), "action_set"),
        ("action_set", ("nearest", "unsafe value"), "action_set"),
        ("constraint_status", "UNKNOWN", "constraint_status"),
    ],
)
def test_tick_validation_covers_identity_digest_and_boundaries(
    field: str, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        RadsTick(**cast(dict[str, Any], tick(**{field: value})))


def test_failure_and_recorder_views_are_serializable() -> None:
    recorder = RadsInstrumentationRecorder()
    recorded = recorder.record(**tick())
    assert recorded.as_dict()["schema_version"] == "routemind-rads-tick-v1"
    failure = recorder.record_failure(
        run_id="run-1", tick=1, reason="missing", missing_fields=("x",)
    )
    assert failure.as_dict()["status"] == "FAILED"
    assert recorder.ticks and recorder.failures
    with pytest.raises(ValueError, match="failure reason"):
        recorder.record_failure(run_id="run-1", tick=1, reason=" ", missing_fields=("x",))
    with pytest.raises(ValueError, match="missing_fields"):
        recorder.record_failure(run_id="run-1", tick=1, reason="missing", missing_fields=("x", "x"))


def test_missing_fields_without_valid_identity_are_not_recorded() -> None:
    recorder = RadsInstrumentationRecorder()
    with pytest.raises(ValueError, match="required instrumentation"):
        recorder.record(run_id=7, tick="bad")
    assert not recorder.failures
