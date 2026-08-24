from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_calibration import (
    execute_bounded_twin_calibration,
    load_twin_calibration_plan,
)
from routemind_compute.application.twin_drift import (
    TwinDriftError,
    TwinDriftPlan,
    execute_twin_drift_report,
    load_twin_drift_plan,
)
from routemind_compute.application.twin_fidelity_protocol import load_twin_fidelity_protocol
from routemind_compute.application.twin_held_out_validation import (
    TwinHeldOutValidationOutcome,
    execute_twin_held_out_validation,
    load_twin_held_out_validation_plan,
)
from routemind_compute.application.twin_split_contract import (
    TwinSplitContract,
    load_twin_split_contract,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-334-calibration-drift-v1.json"
CALIBRATION = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-331-calibration-plan-v1.json"
)
VALIDATION = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-332-held-out-validation-v1.json"
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
    path = tmp_path / "drift.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _loaded() -> tuple[TwinDriftPlan, TwinSplitContract, TwinHeldOutValidationOutcome]:
    drift = load_twin_drift_plan(PLAN)
    split = load_twin_split_contract(SPLIT)
    calibration = load_twin_calibration_plan(CALIBRATION)
    protocol = load_twin_fidelity_protocol(PROTOCOL)
    validation_plan = load_twin_held_out_validation_plan(VALIDATION)
    calibration_outcome = execute_bounded_twin_calibration(calibration, split, protocol)
    validation_outcome = execute_twin_held_out_validation(
        validation_plan, split, protocol, calibration, calibration_outcome
    )
    return drift, split, validation_outcome


def test_drift_report_separates_parameter_and_fidelity_no_data() -> None:
    drift, split, validation_outcome = _loaded()
    assert drift.drift_id == "r3-334-calibration-drift-v1"
    outcome = execute_twin_drift_report(drift, split, validation_outcome)
    assert outcome.status == "INSUFFICIENT_DATA"
    assert outcome.parameter_drift_status == "NOT_ANALYZED_NO_DATA"
    assert outcome.fidelity_degradation_status == "NOT_ANALYZED_NO_DATA"
    assert [regime.axis for regime in outcome.regimes] == ["time", "zone", "demand", "traffic"]
    assert all(regime.record_count == 0 for regime in outcome.regimes)
    assert all(
        regime.parameter_drift_status == "NOT_ANALYZED_NO_DATA"
        and regime.fidelity_degradation_status == "NOT_ANALYZED_NO_DATA"
        for regime in outcome.regimes
    )
    assert outcome.reason.startswith("No authorized")


def test_plan_rejects_digest_json_identity_and_shape(tmp_path: Path) -> None:
    payload = _payload()
    payload["question"] = "changed"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TwinDriftError, match="digest"):
        load_twin_drift_plan(forged)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(TwinDriftError, match="JSON object"):
        load_twin_drift_plan(scalar)

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(TwinDriftError, match="UTF-8 JSON"):
        load_twin_drift_plan(invalid)

    payload = _payload()
    del payload["question"]
    with pytest.raises(TwinDriftError, match="fields mismatch"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["task_id"] = "R3-333"
    with pytest.raises(TwinDriftError, match="identity"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["claim_boundary"] = "other"
    with pytest.raises(TwinDriftError, match="claim boundary"):
        load_twin_drift_plan(_write(tmp_path, payload))


def test_plan_rejects_regime_and_policy_drift(tmp_path: Path) -> None:
    payload = _payload()
    payload["regime_axes"] = ["time"]
    with pytest.raises(TwinDriftError, match="regime axes"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["parameter_drift_policy"])
    policy["metrics"] = ["other"]
    payload["parameter_drift_policy"] = policy
    with pytest.raises(TwinDriftError, match="parameter drift metrics"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["parameter_drift_policy"])
    policy["require_before_after_checksums"] = False
    payload["parameter_drift_policy"] = policy
    with pytest.raises(TwinDriftError, match="before/after"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["fidelity_degradation_policy"])
    policy["baseline"] = "other"
    payload["fidelity_degradation_policy"] = policy
    with pytest.raises(TwinDriftError, match="baseline"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    data = _mapping(payload["data_policy"])
    data["recalibration_is_solution"] = True
    payload["data_policy"] = data
    with pytest.raises(TwinDriftError, match="unsafe claims"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["parameter_drift_policy"])
    policy["missing_status"] = "other"
    payload["parameter_drift_policy"] = policy
    with pytest.raises(TwinDriftError, match="missing parameter"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["fidelity_degradation_policy"])
    policy["metrics"] = ["other"]
    payload["fidelity_degradation_policy"] = policy
    with pytest.raises(TwinDriftError, match="fidelity degradation metrics"):
        load_twin_drift_plan(_write(tmp_path, payload))


def test_plan_rejects_nested_types_and_missing_status(tmp_path: Path) -> None:
    payload = _payload()
    payload["regime_axes"] = "invalid"
    with pytest.raises(TwinDriftError, match="array"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["regime_axes"] = [1, "zone", "demand", "traffic"]
    with pytest.raises(TwinDriftError, match="regime axis"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["parameter_drift_policy"] = "invalid"
    with pytest.raises(TwinDriftError, match="object"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["fidelity_degradation_policy"])
    policy["missing_status"] = "other"
    payload["fidelity_degradation_policy"] = policy
    with pytest.raises(TwinDriftError, match="missing fidelity"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    data = _mapping(payload["data_policy"])
    data["no_synthetic_data"] = "yes"
    payload["data_policy"] = data
    with pytest.raises(TwinDriftError, match="boolean"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    data = _mapping(payload["data_policy"])
    data["held_out_split_id"] = data["calibration_split_id"]
    payload["data_policy"] = data
    with pytest.raises(TwinDriftError, match="distinct"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["question"] = ""
    with pytest.raises(TwinDriftError, match="non-empty text"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["parameter_drift_policy"])
    policy["unexpected"] = True
    payload["parameter_drift_policy"] = policy
    with pytest.raises(TwinDriftError, match="fields mismatch"):
        load_twin_drift_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["source_validation_plan_digest"] = "g" * 64
    with pytest.raises(TwinDriftError, match="SHA-256"):
        load_twin_drift_plan(_write(tmp_path, payload))


def test_executor_rejects_lineage_and_non_data_branch() -> None:
    drift, split, validation_outcome = _loaded()
    altered = TwinHeldOutValidationOutcome(
        validation_outcome.outcome,
        "a" * 64,
        validation_outcome.split_contract_digest,
        validation_outcome.fidelity_protocol_digest,
        validation_outcome.calibration_status,
        validation_outcome.held_out_record_count,
        validation_outcome.metrics,
        validation_outcome.reason,
    )
    with pytest.raises(TwinDriftError, match="validation plan digest"):
        execute_twin_drift_report(drift, split, altered)

    non_insufficient = TwinHeldOutValidationOutcome(
        "VALIDATED_FOR_SCOPE",
        validation_outcome.plan_digest,
        validation_outcome.split_contract_digest,
        validation_outcome.fidelity_protocol_digest,
        validation_outcome.calibration_status,
        validation_outcome.held_out_record_count,
        validation_outcome.metrics,
        validation_outcome.reason,
    )
    with pytest.raises(TwinDriftError, match="explicit held-out"):
        execute_twin_drift_report(drift, split, non_insufficient)

    drift_payload = dict(drift.payload)
    drift_payload["split_contract_digest"] = "a" * 64
    altered_drift = TwinDriftPlan(drift_payload, drift.plan_digest, drift.manifest_sha256)
    with pytest.raises(TwinDriftError, match="split contract digest"):
        execute_twin_drift_report(altered_drift, split, validation_outcome)

    data_policy = _mapping(drift.payload["data_policy"])
    data_policy["calibration_split_id"] = "other"
    altered_drift = TwinDriftPlan(
        {**drift.payload, "data_policy": data_policy},
        drift.plan_digest,
        drift.manifest_sha256,
    )
    with pytest.raises(TwinDriftError, match="calibration split identity"):
        execute_twin_drift_report(altered_drift, split, validation_outcome)

    data_policy = _mapping(drift.payload["data_policy"])
    data_policy["held_out_split_id"] = "other"
    altered_drift = TwinDriftPlan(
        {**drift.payload, "data_policy": data_policy},
        drift.plan_digest,
        drift.manifest_sha256,
    )
    with pytest.raises(TwinDriftError, match="held-out split identity"):
        execute_twin_drift_report(altered_drift, split, validation_outcome)

    data_policy = _mapping(drift.payload["data_policy"])
    data_policy["no_synthetic_data"] = False
    altered_drift = TwinDriftPlan(
        {**drift.payload, "data_policy": data_policy},
        drift.plan_digest,
        drift.manifest_sha256,
    )
    with pytest.raises(TwinDriftError, match="synthetic data"):
        execute_twin_drift_report(altered_drift, split, validation_outcome)

    split_payload = dict(split.payload)
    split_values = _mapping(split_payload["splits"])
    calibration = _mapping(split_values["calibration"])
    held_out = _mapping(split_values["held_out"])
    calibration["artifact_status"] = "AVAILABLE"
    calibration["record_count"] = 1
    held_out["artifact_status"] = "AVAILABLE"
    held_out["record_count"] = 1
    split_values["calibration"] = calibration
    split_values["held_out"] = held_out
    split_payload["splits"] = split_values
    available = TwinSplitContract(split_payload, split.contract_digest, split.manifest_sha256)
    with pytest.raises(TwinDriftError, match="manifest counts"):
        execute_twin_drift_report(drift, available, validation_outcome)

    split_payload = dict(split.payload)
    split_values = _mapping(split_payload["splits"])
    calibration = _mapping(split_values["calibration"])
    calibration["record_count"] = "0"
    split_values["calibration"] = calibration
    split_payload["splits"] = split_values
    invalid_count = TwinSplitContract(split_payload, split.contract_digest, split.manifest_sha256)
    with pytest.raises(TwinDriftError, match="integer"):
        execute_twin_drift_report(drift, invalid_count, validation_outcome)


def test_plan_file_digest_is_stable() -> None:
    first = load_twin_drift_plan(PLAN)
    second = load_twin_drift_plan(PLAN)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
