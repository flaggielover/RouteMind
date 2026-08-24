from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_calibration import (
    TwinCalibrationOutcome,
    TwinCalibrationPlan,
    execute_bounded_twin_calibration,
    load_twin_calibration_plan,
)
from routemind_compute.application.twin_fidelity_protocol import (
    TwinFidelityProtocol,
    load_twin_fidelity_protocol,
)
from routemind_compute.application.twin_held_out_validation import (
    TwinHeldOutValidationError,
    TwinHeldOutValidationPlan,
    execute_twin_held_out_validation,
    load_twin_held_out_validation_plan,
)
from routemind_compute.application.twin_split_contract import (
    TwinSplitContract,
    load_twin_split_contract,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-332-held-out-validation-v1.json"
)
CALIBRATION_PLAN = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-331-calibration-plan-v1.json"
)
SPLIT = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-330-twin-split-contract-v1.json"
)
PROTOCOL = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-333-fidelity-protocol-v1.json"
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PLAN.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["plan_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "plan_digest"}
    )
    path = tmp_path / "validation.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _loaded() -> tuple[
    TwinHeldOutValidationPlan,
    TwinCalibrationPlan,
    TwinSplitContract,
    TwinFidelityProtocol,
    TwinCalibrationOutcome,
]:
    validation = load_twin_held_out_validation_plan(PLAN)
    calibration_plan = load_twin_calibration_plan(CALIBRATION_PLAN)
    split = load_twin_split_contract(SPLIT)
    protocol = load_twin_fidelity_protocol(PROTOCOL)
    calibration_outcome = execute_bounded_twin_calibration(calibration_plan, split, protocol)
    return validation, calibration_plan, split, protocol, calibration_outcome


def test_held_out_validation_returns_insufficient_data_without_estimates() -> None:
    validation, calibration_plan, split, protocol, calibration_outcome = _loaded()
    assert validation.validation_id == "r3-332-held-out-validation-v1"
    outcome = execute_twin_held_out_validation(
        validation,
        split,
        protocol,
        calibration_plan,
        calibration_outcome,
    )
    assert outcome.outcome == "INSUFFICIENT_DATA"
    assert outcome.held_out_record_count == 0
    assert outcome.calibration_status == "INSUFFICIENT_DATA"
    assert [metric.metric_id for metric in outcome.metrics] == [
        "assignment_rate",
        "scenario_risk_index",
        "dispatch_latency_seconds",
        "fallback_rate",
    ]
    assert all(metric.status == "NOT_REPORTED_NO_DATA" for metric in outcome.metrics)
    assert all(metric.estimate is None and metric.uncertainty is None for metric in outcome.metrics)
    assert outcome.reason.startswith("No held-out estimate")


def test_plan_rejects_digest_json_shape_and_identity(tmp_path: Path) -> None:
    payload = _payload()
    payload["question"] = "changed"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TwinHeldOutValidationError, match="digest"):
        load_twin_held_out_validation_plan(forged)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(TwinHeldOutValidationError, match="JSON object"):
        load_twin_held_out_validation_plan(scalar)

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(TwinHeldOutValidationError, match="UTF-8 JSON"):
        load_twin_held_out_validation_plan(invalid)

    payload = _payload()
    del payload["question"]
    with pytest.raises(TwinHeldOutValidationError, match="fields mismatch"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["task_id"] = "R3-331"
    with pytest.raises(TwinHeldOutValidationError, match="identity"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["claim_boundary"] = "other"
    with pytest.raises(TwinHeldOutValidationError, match="claim boundary"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))


def test_plan_rejects_metric_uncertainty_and_digest_policy_drift(tmp_path: Path) -> None:
    payload = _payload()
    payload["metric_ids"] = ["assignment_rate"]
    with pytest.raises(TwinHeldOutValidationError, match="metric identity"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    uncertainty = _mapping(payload["uncertainty_policy"])
    uncertainty["method"] = "t"
    payload["uncertainty_policy"] = uncertainty
    with pytest.raises(TwinHeldOutValidationError, match="uncertainty method"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    uncertainty = _mapping(payload["uncertainty_policy"])
    uncertainty["confidence_level"] = 0.9
    payload["uncertainty_policy"] = uncertainty
    with pytest.raises(TwinHeldOutValidationError, match="confidence"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    uncertainty = _mapping(payload["uncertainty_policy"])
    uncertainty["minimum_pairs"] = 0
    payload["uncertainty_policy"] = uncertainty
    with pytest.raises(TwinHeldOutValidationError, match="minimum pairs"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["split_contract_digest"] = "x"
    with pytest.raises(TwinHeldOutValidationError, match="SHA-256"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    uncertainty = _mapping(payload["uncertainty_policy"])
    uncertainty["report_when_missing"] = "other"
    payload["uncertainty_policy"] = uncertainty
    with pytest.raises(TwinHeldOutValidationError, match="missing held-out"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    uncertainty = _mapping(payload["uncertainty_policy"])
    uncertainty["minimum_pairs"] = "100"
    payload["uncertainty_policy"] = uncertainty
    with pytest.raises(TwinHeldOutValidationError, match="integer"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    uncertainty = _mapping(payload["uncertainty_policy"])
    uncertainty["confidence_level"] = "0.95"
    payload["uncertainty_policy"] = uncertainty
    with pytest.raises(TwinHeldOutValidationError, match="finite number"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))


def test_plan_rejects_data_and_outcome_policy_drift(tmp_path: Path) -> None:
    payload = _payload()
    data_policy = _mapping(payload["data_policy"])
    data_policy["held_out_split_id"] = data_policy["calibration_split_id"]
    payload["data_policy"] = data_policy
    with pytest.raises(TwinHeldOutValidationError, match="distinct"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    data_policy = _mapping(payload["data_policy"])
    data_policy["retune_on_held_out"] = True
    payload["data_policy"] = data_policy
    with pytest.raises(TwinHeldOutValidationError, match="retuning"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["outcome_policy"])
    policy["allowed_outcomes"] = ["INSUFFICIENT_DATA"]
    payload["outcome_policy"] = policy
    with pytest.raises(TwinHeldOutValidationError, match="four-state"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["outcome_policy"])
    policy["status_when_missing"] = "FAILED_VALIDATION"
    payload["outcome_policy"] = policy
    with pytest.raises(TwinHeldOutValidationError, match="INSUFFICIENT_DATA"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    uncertainty = _mapping(payload["uncertainty_policy"])
    uncertainty["unexpected"] = True
    payload["uncertainty_policy"] = uncertainty
    with pytest.raises(TwinHeldOutValidationError, match="fields mismatch"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["uncertainty_policy"] = "invalid"
    with pytest.raises(TwinHeldOutValidationError, match="object"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["metric_ids"] = "invalid"
    with pytest.raises(TwinHeldOutValidationError, match="array"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["question"] = ""
    with pytest.raises(TwinHeldOutValidationError, match="non-empty text"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["metric_ids"] = [1, "scenario_risk_index", "dispatch_latency_seconds", "fallback_rate"]
    with pytest.raises(TwinHeldOutValidationError, match="metric id"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))

    payload = _payload()
    data_policy = _mapping(payload["data_policy"])
    data_policy["held_out_read_only"] = "yes"
    payload["data_policy"] = data_policy
    with pytest.raises(TwinHeldOutValidationError, match="boolean"):
        load_twin_held_out_validation_plan(_write(tmp_path, payload))


def test_executor_rejects_lineage_and_unsafe_calibration(tmp_path: Path) -> None:
    validation, calibration_plan, split, protocol, calibration_outcome = _loaded()
    payload = _payload()
    payload["source_calibration_plan_digest"] = "a" * 64
    drifted = load_twin_held_out_validation_plan(_write(tmp_path, payload))
    with pytest.raises(TwinHeldOutValidationError, match="calibration plan digest"):
        execute_twin_held_out_validation(
            drifted,
            split,
            protocol,
            calibration_plan,
            calibration_outcome,
        )

    unsafe = TwinCalibrationOutcome(
        "INSUFFICIENT_DATA",
        "other",
        calibration_outcome.split_contract_digest,
        calibration_outcome.fidelity_protocol_digest,
        0,
        0,
        (),
        None,
        None,
        None,
        "reason",
    )
    with pytest.raises(TwinHeldOutValidationError, match="outcome lineage"):
        execute_twin_held_out_validation(
            validation,
            split,
            protocol,
            calibration_plan,
            unsafe,
        )

    unsafe = TwinCalibrationOutcome(
        "CALIBRATED",
        calibration_plan.plan_digest,
        calibration_outcome.split_contract_digest,
        calibration_outcome.fidelity_protocol_digest,
        0,
        0,
        (),
        None,
        None,
        None,
        "reason",
    )
    unsafe_plan = type(calibration_plan)(
        calibration_plan.payload,
        calibration_plan.plan_digest,
        calibration_plan.manifest_sha256,
    )
    with pytest.raises(TwinHeldOutValidationError, match="calibration outcome"):
        execute_twin_held_out_validation(
            validation,
            split,
            protocol,
            unsafe_plan,
            unsafe,
        )

    split_policy = _mapping(validation.payload["data_policy"])
    split_policy["calibration_split_id"] = "other"
    split_drift = TwinHeldOutValidationPlan(
        {**validation.payload, "data_policy": split_policy},
        validation.plan_digest,
        validation.manifest_sha256,
    )
    with pytest.raises(TwinHeldOutValidationError, match="calibration split identity"):
        execute_twin_held_out_validation(
            split_drift, split, protocol, calibration_plan, calibration_outcome
        )

    split_policy = _mapping(validation.payload["data_policy"])
    split_policy["held_out_split_id"] = "other"
    split_drift = TwinHeldOutValidationPlan(
        {**validation.payload, "data_policy": split_policy},
        validation.plan_digest,
        validation.manifest_sha256,
    )
    with pytest.raises(TwinHeldOutValidationError, match="held-out split identity"):
        execute_twin_held_out_validation(
            split_drift, split, protocol, calibration_plan, calibration_outcome
        )

    unsafe_policy = _mapping(validation.payload["data_policy"])
    unsafe_policy["held_out_read_only"] = False
    unsafe_validation_plan = TwinHeldOutValidationPlan(
        {**validation.payload, "data_policy": unsafe_policy},
        validation.plan_digest,
        validation.manifest_sha256,
    )
    with pytest.raises(TwinHeldOutValidationError, match="unsafe retuning"):
        execute_twin_held_out_validation(
            unsafe_validation_plan, split, protocol, calibration_plan, calibration_outcome
        )

    altered_protocol = type(protocol)(
        protocol.payload,
        protocol.protocol_digest,
        protocol.manifest_sha256,
        tuple(reversed(protocol.metrics)),
    )
    with pytest.raises(TwinHeldOutValidationError, match="metric identity"):
        execute_twin_held_out_validation(
            validation, split, altered_protocol, calibration_plan, calibration_outcome
        )


def test_executor_rejects_non_data_branch_and_digest_mismatch() -> None:
    validation, calibration_plan, split, protocol, calibration_outcome = _loaded()
    split_payload = dict(split.payload)
    split_payload["data_availability"] = {
        **_mapping(split_payload["data_availability"]),
        "status": "AVAILABLE",
    }
    available = TwinSplitContract(split_payload, split.contract_digest, split.manifest_sha256)
    with pytest.raises(TwinHeldOutValidationError, match="required"):
        execute_twin_held_out_validation(
            validation,
            available,
            protocol,
            calibration_plan,
            calibration_outcome,
        )

    altered_protocol = type(protocol)(
        protocol.payload,
        "a" * 64,
        protocol.manifest_sha256,
        protocol.metrics,
    )
    with pytest.raises(TwinHeldOutValidationError, match="protocol digest"):
        execute_twin_held_out_validation(
            validation,
            split,
            altered_protocol,
            calibration_plan,
            calibration_outcome,
        )

    altered_validation = TwinHeldOutValidationPlan(
        {**validation.payload, "split_contract_digest": "a" * 64},
        validation.plan_digest,
        validation.manifest_sha256,
    )
    with pytest.raises(TwinHeldOutValidationError, match="split contract digest"):
        execute_twin_held_out_validation(
            altered_validation, split, protocol, calibration_plan, calibration_outcome
        )

    split_payload = dict(split.payload)
    split_values = _mapping(split_payload["splits"])
    held_out = _mapping(split_values["held_out"])
    held_out["artifact_status"] = "AVAILABLE"
    held_out["record_count"] = 1
    split_values["held_out"] = held_out
    split_payload["splits"] = split_values
    available_records = TwinSplitContract(
        split_payload, split.contract_digest, split.manifest_sha256
    )
    with pytest.raises(TwinHeldOutValidationError, match="manifest counts"):
        execute_twin_held_out_validation(
            validation, available_records, protocol, calibration_plan, calibration_outcome
        )


def test_plan_file_digest_is_stable() -> None:
    first = load_twin_held_out_validation_plan(PLAN)
    second = load_twin_held_out_validation_plan(PLAN)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
